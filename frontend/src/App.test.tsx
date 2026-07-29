import { render, screen } from "@testing-library/react";
import App from "./App";

describe("QuestPilot shell", () => {
  it("renders the full mission route and verification promise", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "QuestPilot" })).toBeInTheDocument();
    expect(screen.getByLabelText("任务航线")).toBeInTheDocument();
    expect(screen.getByText("可验证模式")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "合并计算材料缺口" })).toBeDisabled();
  });
});
