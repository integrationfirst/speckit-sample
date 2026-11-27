import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

const WELCOME_TEXT = /foundation for upcoming features/;

describe("App", () => {
  it("renders the top-level heading with the app name", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { level: 1, name: /speckit-sample/ }),
    ).toBeInTheDocument();
  });

  it("shows the app name in the banner", () => {
    render(<App />);

    expect(
      within(screen.getByRole("banner")).getByText("speckit-sample"),
    ).toBeInTheDocument();
  });

  it("puts exactly one level-1 heading and the welcome message in main", () => {
    render(<App />);
    const main = screen.getByRole("main");

    expect(within(main).getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(within(main).getByText(WELCOME_TEXT)).toBeInTheDocument();
  });

  it("renders a footer (contentinfo) landmark", () => {
    render(<App />);

    expect(screen.getByRole("contentinfo")).toBeInTheDocument();
  });

  it("has exactly one level-1 heading on the whole page", () => {
    render(<App />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });
});
