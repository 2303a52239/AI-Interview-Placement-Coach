import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { Button } from "@/components/ui/button";
import { RubricBars } from "@/components/ui/RubricBars";
import { Badge } from "@/components/ui/badge";

describe("Button", () => {
  it("fires onClick and respects disabled", async () => {
    const onClick = vi.fn();
    const { rerender } = render(<Button onClick={onClick}>Save</Button>);
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onClick).toHaveBeenCalledTimes(1);
    rerender(<Button onClick={onClick} disabled>Save</Button>);
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

describe("RubricBars", () => {
  it("shows each criterion with its rounded score and rationale", () => {
    render(<RubricBars rubric={{ correctness: { score: 82.4, rationale: "Covers the core idea" }, communication: { score: 40 } }} />);
    expect(screen.getByText("Correctness")).toBeInTheDocument();
    expect(screen.getByText("82")).toBeInTheDocument();
    expect(screen.getByText("Covers the core idea")).toBeInTheDocument();
    expect(screen.getByText("Communication")).toBeInTheDocument();
  });
  it("renders nothing for an empty rubric", () => {
    const { container } = render(<RubricBars rubric={{}} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("Badge", () => {
  it("renders its children", () => {
    render(<Badge tone="teal">strong</Badge>);
    expect(screen.getByText("strong")).toBeInTheDocument();
  });
});
