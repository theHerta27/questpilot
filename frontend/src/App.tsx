import { FormEvent, useMemo, useState } from "react";
import {
  Activity,
  Boxes,
  ChevronRight,
  Database,
  Gauge,
  Search,
  ShieldCheck,
  Sparkles
} from "lucide-react";
import { api } from "./api";
import { RouteRail } from "./components/RouteRail";
import { StatusPill } from "./components/StatusPill";
import type { Character, GapResult, PlanResult, SkillGoal } from "./types";

type View = "mission" | "trace";

export default function App() {
  const [view, setView] = useState<View>("mission");
  const [query, setQuery] = useState("阿尔托莉雅");
  const [characters, setCharacters] = useState<Character[]>([]);
  const [selected, setSelected] = useState<Character | null>(null);
  const [skill, setSkill] = useState(1);
  const [currentLevel, setCurrentLevel] = useState(1);
  const [targetLevel, setTargetLevel] = useState(6);
  const [inventory, setInventory] = useState<Record<number, number>>({});
  const [gap, setGap] = useState<GapResult | null>(null);
  const [plan, setPlan] = useState<PlanResult | null>(null);
  const [currentAp, setCurrentAp] = useState(140);
  const [apples, setApples] = useState(2);
  const [traceRunId, setTraceRunId] = useState("");
  const [trace, setTrace] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const goal: SkillGoal | null = selected
    ? {
        character_id: selected.id,
        skill_number: skill,
        current_level: currentLevel,
        target_level: targetLevel
      }
    : null;

  const activeStage = plan ? 4 : gap ? 3 : selected ? 1 : 0;
  const totalGap = useMemo(
    () => gap?.items.reduce((sum, item) => sum + item.gap, 0) ?? 0,
    [gap]
  );

  async function handleSearch(event: FormEvent) {
    event.preventDefault();
    setBusy("search");
    setError("");
    try {
      const result = await api.searchCharacters(query);
      setCharacters(result);
      if (result.length === 1) setSelected(result[0]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "角色查询失败");
    } finally {
      setBusy("");
    }
  }

  async function calculate() {
    if (!goal) return;
    setBusy("gap");
    setError("");
    try {
      await api.replaceInventory(
        Object.entries(inventory).map(([materialId, quantity]) => ({
          material_id: Number(materialId),
          quantity
        }))
      );
      const result = await api.calculateGap([goal]);
      setGap(result);
      setPlan(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "缺口计算失败");
    } finally {
      setBusy("");
    }
  }

  async function createPlan() {
    if (!goal) return;
    setBusy("plan");
    setError("");
    try {
      const result = await api.createPlan([goal], currentAp, apples);
      setPlan(result);
      setTraceRunId(result.run_id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "路线生成失败");
    } finally {
      setBusy("");
    }
  }

  async function loadTrace(kind: "trace" | "replay") {
    if (!traceRunId.trim()) return;
    setBusy(kind);
    setError("");
    try {
      const result =
        kind === "trace"
          ? await api.trace(traceRunId.trim())
          : await api.replay(traceRunId.trim());
      setTrace(result);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "运行记录读取失败");
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="min-h-screen bg-paper text-slate-900">
      <header className="command-header">
        <div className="star-grid" aria-hidden />
        <div className="relative mx-auto max-w-7xl px-5 py-6 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-5">
            <div className="flex items-center gap-3">
              <span className="brand-mark"><Sparkles aria-hidden /></span>
              <div>
                <p className="eyebrow text-teal-200">CHALDEA ROUTE CONTROL</p>
                <h1 className="text-2xl font-semibold tracking-tight text-white">QuestPilot</h1>
              </div>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="header-chip"><Database aria-hidden /> Atlas CN</span>
              <span className="header-chip"><ShieldCheck aria-hidden /> 可验证模式</span>
            </div>
          </div>
          <div className="mt-7">
            <RouteRail active={activeStage} />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-5 pb-16 pt-7 lg:px-8">
        <div className="mb-6 flex items-center justify-between border-b border-slate-300">
          <nav aria-label="工作台视图" className="flex gap-6">
            <button className={`tab ${view === "mission" ? "active" : ""}`} onClick={() => setView("mission")}>
              <Boxes aria-hidden />任务编成
            </button>
            <button className={`tab ${view === "trace" ? "active" : ""}`} onClick={() => setView("trace")}>
              <Activity aria-hidden />Trace / Replay
            </button>
          </nav>
          <span className="hidden pb-3 text-xs font-medium text-slate-500 md:block">
            精确数值由确定性代码复核
          </span>
        </div>

        {error && <div role="alert" className="error-banner">{error}</div>}

        {view === "mission" ? (
          <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
            <section className="space-y-6">
              <div className="panel">
                <div className="panel-heading">
                  <span className="step-index">01</span>
                  <div><h2>锁定培养目标</h2><p>中文名、日文名与别名统一解析</p></div>
                </div>
                <form className="search-row" onSubmit={handleSearch}>
                  <label className="sr-only" htmlFor="character-query">角色名称</label>
                  <Search aria-hidden />
                  <input id="character-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="例如：阿尔托莉雅 / 蓝呆" />
                  <button className="primary-button" disabled={busy === "search"}>
                    {busy === "search" ? "查询中…" : "检索"}
                  </button>
                </form>
                {characters.length > 0 && (
                  <div className="result-list" aria-label="角色搜索结果">
                    {characters.map((character) => (
                      <button
                        key={character.id}
                        className={selected?.id === character.id ? "selected" : ""}
                        onClick={() => { setSelected(character); setGap(null); setPlan(null); }}
                      >
                        <span className="rarity">{"★".repeat(character.rarity)}</span>
                        <span><strong>{character.name_zh_cn}</strong><small>{character.class_name} · No.{character.collection_no}</small></span>
                        <ChevronRight aria-hidden />
                      </button>
                    ))}
                  </div>
                )}
                {selected && (
                  <div className="goal-grid">
                    <div className="selected-character">
                      <span className="eyebrow">当前目标</span>
                      <strong>{selected.name_zh_cn}</strong>
                      <small>{selected.aliases.join(" · ") || selected.name_ja}</small>
                    </div>
                    <label>技能<select value={skill} onChange={(e) => setSkill(Number(e.target.value))}><option value={1}>技能一</option><option value={2}>技能二</option><option value={3}>技能三</option></select></label>
                    <label>当前等级<input type="number" min={1} max={10} value={currentLevel} onChange={(e) => setCurrentLevel(Number(e.target.value))} /></label>
                    <label>目标等级<input type="number" min={currentLevel} max={10} value={targetLevel} onChange={(e) => setTargetLevel(Number(e.target.value))} /></label>
                  </div>
                )}
              </div>

              <div className="panel">
                <div className="panel-heading">
                  <span className="step-index">02</span>
                  <div><h2>核对库存与缺口</h2><p>库存可在首次计算后逐项校准</p></div>
                </div>
                {gap ? (
                  <div className="overflow-x-auto">
                    <table>
                      <thead><tr><th>材料</th><th>需求</th><th>库存</th><th>缺口</th></tr></thead>
                      <tbody>
                        {gap.items.map((item) => (
                          <tr key={item.material_id}>
                            <td>{item.material_name}</td>
                            <td>{item.required}</td>
                            <td>
                              <label className="sr-only" htmlFor={`inventory-${item.material_id}`}>{item.material_name}库存</label>
                              <input id={`inventory-${item.material_id}`} className="table-input" type="number" min={0} value={inventory[item.material_id] ?? item.owned} onChange={(e) => setInventory({ ...inventory, [item.material_id]: Number(e.target.value) })} />
                            </td>
                            <td><strong className={item.gap ? "text-orange-700" : "text-teal-700"}>{item.gap}</strong></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <button className="secondary-button mt-4" onClick={calculate}>按新库存重新核算</button>
                  </div>
                ) : (
                  <div className="empty-state"><Gauge aria-hidden /><p>选择角色与技能等级后，生成第一份确定性缺口清单。</p></div>
                )}
                {!gap && <button className="primary-button mt-5 w-full justify-center" disabled={!selected || busy === "gap"} onClick={calculate}>{busy === "gap" ? "正在复核…" : "计算材料缺口"}</button>}
              </div>
            </section>

            <aside className="space-y-6">
              <div className="mission-summary">
                <p className="eyebrow text-teal-700">MISSION BRIEF</p>
                <h2>{selected ? selected.name_zh_cn : "等待选择目标"}</h2>
                <div className="summary-metrics">
                  <span><small>技能目标</small><strong>{selected ? `${currentLevel} → ${targetLevel}` : "—"}</strong></span>
                  <span><small>材料缺口</small><strong>{gap ? totalGap : "—"}</strong></span>
                  <span><small>验证状态</small><strong>{gap?.verified ? "通过" : "待计算"}</strong></span>
                </div>
              </div>

              <div className="panel">
                <div className="panel-heading">
                  <span className="step-index">03</span>
                  <div><h2>设定资源边界</h2><p>路线不会超过这里声明的可用资源</p></div>
                </div>
                <div className="form-grid">
                  <label>当前体力<input type="number" min={0} value={currentAp} onChange={(e) => setCurrentAp(Number(e.target.value))} /></label>
                  <label>黄金果实<input type="number" min={0} value={apples} onChange={(e) => setApples(Number(e.target.value))} /></label>
                </div>
                <button className="primary-button mt-5 w-full justify-center" disabled={!gap || busy === "plan"} onClick={createPlan}>
                  {busy === "plan" ? "规划与验证中…" : "生成局部最优路线"}
                </button>
              </div>

              {plan && (
                <div className="panel route-result">
                  <div className="flex items-start justify-between gap-4">
                    <div><p className="eyebrow">ROUTE RESULT</p><h2>任务路线已生成</h2></div>
                    <StatusPill status={plan.status} />
                  </div>
                  <div className="dataset-line"><Database aria-hidden /><span>{plan.dataset_version ?? "无数据版本"}</span><small>{plan.candidate_scope}</small></div>
                  <div className="route-steps">
                    {plan.steps.length ? plan.steps.map((step, index) => (
                      <div className="route-step" key={step.quest_id}>
                        <span>{String(index + 1).padStart(2, "0")}</span>
                        <div><strong>{step.quest_name}</strong><small>关卡 {step.quest_id} · 样本 {step.sample_runs.toLocaleString()}</small></div>
                        <b>{step.runs} 次</b>
                      </div>
                    )) : <p className="text-sm text-slate-600">当前候选集中没有可验证路线。</p>}
                  </div>
                  <div className="ap-meter"><span style={{ width: `${Math.min(100, (plan.total_ap / Math.max(1, plan.available_ap)) * 100)}%` }} /></div>
                  <div className="flex justify-between text-sm"><span>预计消耗 {plan.total_ap} AP</span><span>可用 {plan.available_ap} AP</span></div>
                  <ul className="warning-list">{plan.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
                </div>
              )}
            </aside>
          </div>
        ) : (
          <section className="grid gap-6 lg:grid-cols-[360px_1fr]">
            <div className="panel h-fit">
              <div className="panel-heading"><span className="step-index"><Activity aria-hidden /></span><div><h2>运行取证</h2><p>定位模型、工具、节点或数据源</p></div></div>
              <label className="field-label" htmlFor="run-id">Run ID</label>
              <input id="run-id" className="standalone-input" value={traceRunId} onChange={(e) => setTraceRunId(e.target.value)} placeholder="生成路线后自动填入" />
              <div className="mt-4 grid grid-cols-2 gap-3">
                <button className="primary-button justify-center" onClick={() => loadTrace("trace")}>加载 Trace</button>
                <button className="secondary-button justify-center" onClick={() => loadTrace("replay")}>Replay 包</button>
              </div>
            </div>
            <div className="panel min-h-[420px]">
              <div className="panel-heading"><span className="step-index"><ShieldCheck aria-hidden /></span><div><h2>证据记录</h2><p>事件顺序、Checkpoint 与版本输入</p></div></div>
              {trace ? <pre className="trace-output">{JSON.stringify(trace, null, 2)}</pre> : <div className="empty-state min-h-72"><Activity aria-hidden /><p>输入一次运行 ID 查看完整证据链。</p></div>}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
