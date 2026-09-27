import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LoginForm } from "@/components/operator/login-form";
import { OperatorControls } from "@/components/operator/operator-controls";

afterEach(() => { vi.restoreAllMocks(); window.localStorage.clear(); });

describe("operator keyboard access", () => {
  it("points command destinations back to the overview from experiments", () => {
    render(<OperatorControls onOverview={false} />);
    fireEvent.click(screen.getByRole("button", { name: "Open command palette" }));
    expect(screen.getByRole("link", { name: /System status/ })).toHaveAttribute("href", "/#system");
    expect(screen.getByRole("link", { name: /Activity log/ })).toHaveAttribute("href", "/#activity");
  });

  it("opens the labeled command dialog with Cmd+K and returns focus on Escape", async () => {
    render(<OperatorControls />);
    const trigger = screen.getByRole("button", { name: "Open command palette" });
    trigger.focus();
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    const dialog = screen.getByRole("dialog", { name: "Navigate the control desk" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    await waitFor(() => expect(screen.getByRole("searchbox")).toHaveFocus());
    fireEvent.keyDown(screen.getByRole("searchbox"), { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("keeps keyboard focus inside the open command dialog", async () => {
    render(<OperatorControls />);
    fireEvent.click(screen.getByRole("button", { name: "Open command palette" }));
    const search = screen.getByRole("searchbox");
    await waitFor(() => expect(search).toHaveFocus());
    fireEvent.keyDown(search, { key: "Tab", shiftKey: true });
    expect(screen.getByRole("link", { name: /Activity log/ })).toHaveFocus();
  });

  it("labels the password field and keeps sign-in disabled until it has a value", () => {
    render(<LoginForm />);
    const input = screen.getByLabelText("Operator password");
    const submit = screen.getByRole("button", { name: "Sign in" });
    expect(input).toHaveAttribute("autocomplete", "current-password");
    expect(submit).toBeDisabled();
    fireEvent.change(input, { target: { value: "example" } });
    expect(submit).toBeEnabled();
  });
});
