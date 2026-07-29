import { Check, Circle, Compass, PackageOpen, Route, ShieldCheck } from "lucide-react";

const stages = [
  { label: "目标", icon: Compass },
  { label: "库存", icon: PackageOpen },
  { label: "缺口", icon: Check },
  { label: "路线", icon: Route },
  { label: "验证", icon: ShieldCheck }
];

export function RouteRail({ active }: { active: number }) {
  return (
    <ol aria-label="任务航线" className="route-rail">
      {stages.map((stage, index) => {
        const Icon = stage.icon;
        const complete = index < active;
        const current = index === active;
        return (
          <li
            className={current ? "current" : complete ? "complete" : ""}
            key={stage.label}
            aria-current={current ? "step" : undefined}
          >
            <span className="route-marker">
              {complete ? <Check aria-hidden /> : current ? <Icon aria-hidden /> : <Circle aria-hidden />}
            </span>
            <span>{stage.label}</span>
          </li>
        );
      })}
    </ol>
  );
}
