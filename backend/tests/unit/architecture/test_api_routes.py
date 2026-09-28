"""The registered HTTP surface delegates each use case once."""

import ast
import inspect
import json
import textwrap
from pathlib import Path

from fastapi.routing import APIRoute

from alon_ai.api.app import create_app


def _application_handlers():
    handlers = []
    for route in create_app().routes:
        candidates = getattr(getattr(route, "original_router", None), "routes", [route])
        handlers.extend(
            candidate.endpoint
            for candidate in candidates
            if isinstance(candidate, APIRoute)
        )
    return handlers


def _delegation_error(function: ast.AsyncFunctionDef | ast.FunctionDef) -> str | None:
    body = [
        node
        for node in function.body
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Constant)
    ]
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        return "handler body must be one return"
    value = body[0].value
    if isinstance(value, ast.Await):
        value = value.value
    if not isinstance(value, ast.Call) or not isinstance(value.func, ast.Attribute):
        return "return must call a service method"
    owner = value.func.value
    if not isinstance(owner, ast.Name) or not (
        owner.id == "service" or owner.id.endswith("_service")
    ):
        return "call target must be an injected service"
    parameters = [
        argument.arg for argument in function.args.args + function.args.kwonlyargs
    ]
    if owner.id not in parameters:
        return "service must be a handler parameter"
    expected = [name for name in parameters if name != owner.id]
    if any(not isinstance(argument, ast.Name) for argument in value.args):
        return "forward unchanged handler arguments"
    positional = [
        argument.id for argument in value.args if isinstance(argument, ast.Name)
    ]
    if positional != expected[: len(positional)]:
        return "forward positional arguments in handler order"
    if any(
        keyword.arg is None
        or not isinstance(keyword.value, ast.Name)
        or keyword.arg != keyword.value.id
        for keyword in value.keywords
    ):
        return "forward named arguments unchanged"
    named = [keyword.arg for keyword in value.keywords]
    if len(named) != len(set(named)) or set(named) != set(expected[len(positional) :]):
        return "forward every handler argument exactly once"
    return None


def _expected_delegations() -> dict[str, dict]:
    fixture = Path(__file__).with_name("backend_layout.json")
    handlers = json.loads(fixture.read_text(encoding="utf-8"))["handlers"]
    return {row["handler"]: row["delegation"] for row in handlers}


def _contract_error(
    function: ast.AsyncFunctionDef | ast.FunctionDef, expected: dict
) -> str | None:
    structural_error = _delegation_error(function)
    if structural_error:
        return structural_error
    statement = function.body[-1]
    assert isinstance(statement, ast.Return)
    expression = statement.value
    assert expression is not None
    call = expression.value if isinstance(expression, ast.Await) else expression
    assert isinstance(call, ast.Call)
    assert isinstance(call.func, ast.Attribute)
    assert all(isinstance(node, ast.Name) for node in call.args)
    assert all(isinstance(node.value, ast.Name) for node in call.keywords)
    actual = {
        "method": call.func.attr,
        "args": [node.id for node in call.args if isinstance(node, ast.Name)],
        "kwargs": {
            node.arg: node.value.id
            for node in call.keywords
            if node.arg is not None and isinstance(node.value, ast.Name)
        },
    }
    return (
        None
        if actual == expected
        else f"delegation differs from checked contract: {actual}"
    )


def test_every_registered_handler_delegates_once() -> None:
    handlers = _application_handlers()
    assert len(handlers) >= 15, "route discovery must not pass vacuously"
    expected = _expected_delegations()
    assert len(expected) == len(handlers) == 28
    failures = []
    for handler in handlers:
        tree = ast.parse(textwrap.dedent(inspect.getsource(handler)))
        function = next(
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        key = f"{handler.__module__}.{handler.__name__}"
        error = _contract_error(function, expected[key])
        if error:
            failures.append(f"{handler.__module__}.{handler.__name__}: {error}")
    assert not failures, "\n".join(failures)


def test_checker_rejects_route_logic_and_hidden_forwarding() -> None:
    invalid = [
        "async def route(service, body):\n    if body: return await service.create(body)\n    return None\n",
        "async def route(service, body):\n    return await service.create(body.model_dump())\n",
        "async def route(service, body):\n    return await helper(body)\n",
        "async def route(service, body):\n    return await service.create()\n",
        "async def route(service, a, b):\n    return await service.create(b, a)\n",
    ]
    for source in invalid:
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.AsyncFunctionDef)
        assert _delegation_error(function) is not None
    wrong_method = ast.parse(
        "async def route(service, body):\n    return await service.delete(body)\n"
    ).body[0]
    assert isinstance(wrong_method, ast.AsyncFunctionDef)
    assert (
        _contract_error(
            wrong_method, {"method": "create", "args": ["body"], "kwargs": {}}
        )
        is not None
    )


def _recording_service(method_name, awaited, calls, returned):
    class FakeService:
        def __getattr__(self, name):
            assert name == method_name
            if awaited:

                async def async_invoke(*args, **kwargs):
                    calls.append((args, kwargs))
                    return returned

                return async_invoke

            def sync_invoke(*args, **kwargs):
                calls.append((args, kwargs))
                return returned

            return sync_invoke

    return FakeService()


async def test_registered_handlers_forward_arguments_once_to_fake_services() -> None:
    expected = _expected_delegations()
    for handler in _application_handlers():
        tree = ast.parse(textwrap.dedent(inspect.getsource(handler)))
        function = next(
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        key = f"{handler.__module__}.{handler.__name__}"
        contract = expected[key]
        assert _contract_error(function, contract) is None
        returned = object()
        calls = []
        return_statement = function.body[-1]
        assert isinstance(return_statement, ast.Return)
        expression = return_statement.value
        assert expression is not None
        awaited = isinstance(expression, ast.Await)
        call = expression.value if awaited else expression
        assert isinstance(call, ast.Call)
        assert isinstance(call.func, ast.Attribute)
        assert isinstance(call.func.value, ast.Name)
        method_name = call.func.attr

        owner = call.func.value.id
        values = {name: object() for name in inspect.signature(handler).parameters}
        values[owner] = _recording_service(method_name, awaited, calls, returned)
        result = handler(**values)
        if inspect.isawaitable(result):
            result = await result
        assert result is returned, handler.__qualname__
        assert all(isinstance(node, ast.Name) for node in call.args)
        assert all(
            node.arg is not None and isinstance(node.value, ast.Name)
            for node in call.keywords
        )
        expected_args = tuple(values[name] for name in contract["args"])
        expected_kwargs = {
            key: values[name] for key, name in contract["kwargs"].items()
        }
        assert calls == [(expected_args, expected_kwargs)], handler.__qualname__


def test_public_method_and_path_set_matches_minimal_intake() -> None:
    paths = create_app().openapi()["paths"]
    actual = {(method.upper(), path) for path, item in paths.items() for method in item}
    assert actual == {
        ("POST", "/auth/login"),
        ("POST", "/auth/logout"),
        ("GET", "/auth/session"),
        ("GET", "/health/live"),
        ("GET", "/health/ready"),
        ("GET", "/operator/activity"),
        ("GET", "/operator/activity/events"),
        ("POST", "/operator/experiments"),
        ("GET", "/operator/experiments/runtime"),
        ("GET", "/operator/experiments/{experiment_id}"),
        ("GET", "/operator/experiments/{experiment_id}/research-case"),
        ("POST", "/operator/experiments/{experiment_id}/accept"),
        ("POST", "/operator/experiments/{experiment_id}/discover"),
        ("POST", "/operator/experiments/{experiment_id}/refine"),
        ("POST", "/operator/experiments/{experiment_id}/returns/refine"),
        ("POST", "/operator/experiments/{experiment_id}/select"),
        ("GET", "/operator/status"),
        ("POST", "/operator/ideas/generate"),
        ("POST", "/operator/ideas/{experiment_id}/generate"),
        ("POST", "/operator/ideas/{experiment_id}/revisions"),
        ("POST", "/operator/ideas/{experiment_id}/start"),
        ("POST", "/operator/idea-profile"),
        ("POST", "/operator/experiments/{experiment_id}/agent-runs"),
        ("GET", "/operator/agent-runs/{run_id}"),
        ("GET", "/operator/agent-runs/{run_id}/result"),
        ("GET", "/operator/agent-runs/{run_id}/events"),
        ("POST", "/operator/agent-runs/{run_id}/cancel"),
        ("POST", "/operator/agent-runs/{run_id}/reject"),
    }
