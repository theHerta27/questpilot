import { AlertTriangle, CheckCircle2, CircleSlash2 } from "lucide-react";

export function StatusPill({
  status
}: {
  status: "complete" | "partial" | "no_verified_route";
}) {
  const config = {
    complete: { text: "已验证完成", icon: CheckCircle2, className: "success" },
    partial: { text: "受约束降级", icon: AlertTriangle, className: "warning" },
    no_verified_route: {
      text: "无已验证路线",
      icon: CircleSlash2,
      className: "danger"
    }
  }[status];
  const Icon = config.icon;
  return (
    <span className={`status-pill ${config.className}`}>
      <Icon aria-hidden />
      {config.text}
    </span>
  );
}
