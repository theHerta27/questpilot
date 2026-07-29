import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Activity,
  Boxes,
  CalendarDays,
  ChevronRight,
  Clock3,
  Database,
  Gauge,
  MessageSquareText,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  Trash2
} from "lucide-react";
import { api } from "./api";
import { RouteRail } from "./components/RouteRail";
import { StatusPill } from "./components/StatusPill";
import {
  type GoalEntry,
  upsertGoalLastWins,
  validateGoalLevels
} from "./goalList";
import type {
  Character,
  DataSourceStatus,
  DropDatasetStatus,
  GapResult,
  GoalParseResult,
  PlanResult
} from "./types";

type View = "mission" | "trace";

function AssetImage({ src, alt, className = "" }: { src: string; alt: string; className?: string }) {
  return (
    <img
      className={className}
      src={src}
      alt={alt}
      loading="lazy"
      onError={(event) => {
        event.currentTarget.onerror = null;
        event.currentTarget.src = "/api/v1/assets/quests/0.png";
      }}
    />
  );
}

export default function App() {
  const [view, setView] = useState<View>("mission");
  const [query, setQuery] = useState("阿尔托莉雅");
  const [characters, setCharacters] = useState<Character[]>([]);
  const [selected, setSelected] = useState<Character | null>(null);
  const [goals, setGoals] = useState<GoalEntry[]>([]);
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
  const [dataStatus, setDataStatus] = useState<DataSourceStatus | null>(null);
  const [dropStatus, setDropStatus] = useState<DropDatasetStatus | null>(null);
  const [naturalQuery, setNaturalQuery] = useState("伊阿宋一技能8到9");
  const [parseResult, setParseResult] = useState<GoalParseResult | null>(null);
  const [deadline, setDeadline] = useState("");
  const [dailyMinutes, setDailyMinutes] = useState(60);
  const [minutesPerRun, setMinutesPerRun] = useState(3);

  useEffect(() => {
    api.dataStatus().then(setDataStatus).catch(() => setDataStatus(null));
    api.dropDatasetStatus().then(setDropStatus).catch(() => setDropStatus(null));
  }, []);

  const goalPayload = goals.map(({ character: _character, ...goal }) => goal);
  const activeStage = plan ? 4 : gap ? 3 : goals.length ? 1 : 0;
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
      if (result.length === 1 && !result[0].requires_selection) {
        setSelected(result[0]);
      } else {
        setSelected(null);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "角色查询失败");
    } finally {
      setBusy("");
    }
  }

  async function parseNaturalGoals() {
    if (!naturalQuery.trim()) return;
    setBusy("parse");
    setError("");
    try {
      const result = await api.parseGoals(naturalQuery.trim());
      setParseResult(result);
      setGoals((current) =>
        result.resolved_goals.reduce(
          (nextGoals, goal) => upsertGoalLastWins(nextGoals, goal),
          current
        )
      );
      setGap(null);
      setPlan(null);
      setTraceRunId(result.run_id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "自然语言目标解析失败");
    } finally {
      setBusy("");
    }
  }

  function chooseParsedCandidate(
    group: GoalParseResult["candidate_groups"][number],
    character: Character
  ) {
    const next: GoalEntry = {
      character,
      character_id: character.id,
      skill_number: group.skill_number,
      current_level: group.current_level,
      target_level: group.target_level
    };
    setGoals((current) => upsertGoalLastWins(current, next));
    setParseResult((current) =>
      current
        ? {
            ...current,
            resolved_goals: [...current.resolved_goals, next],
            candidate_groups: current.candidate_groups.filter(
              (item) => item.draft_index !== group.draft_index
            ),
            explanation: "候选已确认并加入目标清单。"
          }
        : current
    );
    setGap(null);
    setPlan(null);
  }

  function addGoal() {
    if (!selected) return;
    try {
      validateGoalLevels(currentLevel, targetLevel);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "技能等级不合法。");
      return;
    }
    const next: GoalEntry = {
      character: selected,
      character_id: selected.id,
      skill_number: skill,
      current_level: currentLevel,
      target_level: targetLevel
    };
    setGoals((current) => upsertGoalLastWins(current, next));
    setGap(null);
    setPlan(null);
    setError("");
  }

  function removeGoal(index: number) {
    setGoals((current) => current.filter((_, itemIndex) => itemIndex !== index));
    setGap(null);
    setPlan(null);
  }

  async function calculate() {
    if (!goalPayload.length) return;
    setBusy("gap");
    setError("");
    try {
      await api.replaceInventory(
        Object.entries(inventory).map(([materialId, quantity]) => ({
          material_id: Number(materialId),
          quantity
        }))
      );
      const result = await api.calculateGap(goalPayload);
      setGap(result);
      setPlan(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "缺口计算失败");
    } finally {
      setBusy("");
    }
  }

  async function createPlan() {
    if (!goalPayload.length) return;
    setBusy("plan");
    setError("");
    try {
      const result = await api.createPlan(
        goalPayload,
        currentAp,
        apples,
        deadline,
        dailyMinutes,
        minutesPerRun
      );
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
              <span className="header-chip">
                <Database aria-hidden />
                Atlas CN {dataStatus ? `· ${dataStatus.version}` : ""}
              </span>
              {dropStatus && (
                <span className="header-chip">
                  掉率 {dropStatus.version} · {dropStatus.candidate_quest_count} 关
                </span>
              )}
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
                {dataStatus && (
                  <div className="source-proof">
                    <Database aria-hidden />
                    <span>
                      <strong>{dataStatus.source} · {dataStatus.region}</strong>
                      <small>
                        版本 {dataStatus.version} · dataVer {dataStatus.data_ver ?? "—"} ·
                        更新 {new Date(dataStatus.fetched_at).toLocaleString("zh-CN")}
                      </small>
                    </span>
                    <a href={dataStatus.source_url} target="_blank" rel="noreferrer">查看来源</a>
                  </div>
                )}
                <div className="agent-briefing">
                  <div className="agent-briefing-title">
                    <MessageSquareText aria-hidden />
                    <span>
                      <strong>用一句话编成目标</strong>
                      <small>模型只解析角色与等级，材料和路线仍由确定性工具计算</small>
                    </span>
                  </div>
                  <label className="sr-only" htmlFor="natural-goal">自然语言培养目标</label>
                  <textarea
                    id="natural-goal"
                    value={naturalQuery}
                    onChange={(event) => setNaturalQuery(event.target.value)}
                    placeholder="例如：伊阿宋一技能8到9，弓刑部二技能4到5"
                  />
                  <button
                    className="agent-action"
                    onClick={parseNaturalGoals}
                    disabled={busy === "parse" || !naturalQuery.trim()}
                  >
                    {busy === "parse" ? "解析中…" : "解析并加入清单"}
                  </button>
                  {parseResult && (
                    <div className="parse-proof" aria-label="模型解析结果">
                      <div className="parse-summary">
                        <strong>{parseResult.explanation}</strong>
                        <small>Run {parseResult.run_id} · {parseResult.event_count} 个事件</small>
                      </div>
                      <ol className="tool-step-list" aria-label="工具调用步骤">
                        {parseResult.tool_steps.map((step, index) => (
                          <li key={`${step.name}-${index}`}>
                            <span>{index + 1}</span>
                            <strong>{step.name}</strong>
                            <small>{step.summary}</small>
                          </li>
                        ))}
                      </ol>
                      {parseResult.resolved_goals.map((goal) => (
                        <div className="parsed-goal" key={`${goal.character_id}-${goal.skill_number}`}>
                          <AssetImage src={goal.character.image_url} alt={`${goal.character.name_zh_cn}角色头像`} />
                          <span>
                            <strong>{goal.character.name_zh_cn}</strong>
                            <small>技能 {goal.skill_number} · {goal.current_level} → {goal.target_level}</small>
                          </span>
                          <b>已加入</b>
                        </div>
                      ))}
                      {parseResult.candidate_groups.map((group) => (
                        <div className="candidate-confirm" key={group.draft_index}>
                          <strong>“{group.character_query}”需要选择角色</strong>
                          {group.candidates.length ? (
                            <div>
                              {group.candidates.map((candidate) => (
                                <button
                                  key={candidate.id}
                                  onClick={() => chooseParsedCandidate(group, candidate)}
                                >
                                  <AssetImage src={candidate.image_url} alt={`${candidate.name_zh_cn}角色头像`} />
                                  <span>{candidate.name_zh_cn}<small>{candidate.class_name} · No.{candidate.collection_no}</small></span>
                                </button>
                              ))}
                            </div>
                          ) : <small>没有足够可信的候选，请改用更完整的角色名称。</small>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div className="manual-divider"><span>或手动检索角色</span></div>
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
                        <AssetImage src={character.image_url} alt={`${character.name_zh_cn}角色头像`} className="character-thumb" />
                        <span>
                          <strong>{character.name_zh_cn}</strong>
                          <small>
                            {character.class_name} · No.{character.collection_no} ·{" "}
                            {character.match_type === "exact_name"
                              ? "精确名称"
                              : character.match_type === "exact_alias"
                                ? "别名命中"
                                : `模糊候选 ${Math.round(character.confidence * 100)}%`}
                          </small>
                          <span className="rarity">{"★".repeat(character.rarity)}</span>
                        </span>
                        <ChevronRight aria-hidden />
                      </button>
                    ))}
                  </div>
                )}
                {characters.some((character) => character.requires_selection) && (
                  <p className="selection-note">存在同名或低置信度候选，请明确选择后再加入目标。</p>
                )}
                {selected && (
                  <>
                    <div className="goal-grid">
                      <div className="selected-character">
                        <AssetImage src={selected.image_url} alt={`${selected.name_zh_cn}角色头像`} />
                        <span>
                          <span className="eyebrow">待加入目标</span>
                          <strong>{selected.name_zh_cn}</strong>
                          <small>{selected.aliases.join(" · ") || selected.name_ja}</small>
                        </span>
                      </div>
                      <label>技能<select value={skill} onChange={(e) => setSkill(Number(e.target.value))}><option value={1}>技能一</option><option value={2}>技能二</option><option value={3}>技能三</option></select></label>
                      <label>当前等级<input type="number" min={1} max={10} value={currentLevel} onChange={(e) => setCurrentLevel(Number(e.target.value))} /></label>
                      <label>目标等级<input type="number" min={currentLevel} max={10} value={targetLevel} onChange={(e) => setTargetLevel(Number(e.target.value))} /></label>
                    </div>
                    <button className="secondary-button mt-4" onClick={addGoal}>
                      <Plus aria-hidden />加入目标清单
                    </button>
                  </>
                )}
                {goals.length > 0 && (
                  <div className="goal-manifest" aria-label="培养目标清单">
                    <div className="manifest-heading">
                      <strong>已编成 {goals.length} 项培养目标</strong>
                      <small>同角色同技能以后一次输入完整覆盖</small>
                    </div>
                    {goals.map((item, index) => (
                      <div className="manifest-row" key={`${item.character_id}-${item.skill_number}`}>
                        <span className="manifest-number">{String(index + 1).padStart(2, "0")}</span>
                        <AssetImage src={item.character.image_url} alt={`${item.character.name_zh_cn}角色头像`} />
                        <span>
                          <strong>{item.character.name_zh_cn}</strong>
                          <small>技能 {item.skill_number} · {item.current_level} → {item.target_level}</small>
                        </span>
                        <button
                          aria-label={`删除 ${item.character.name_zh_cn} 技能 ${item.skill_number}`}
                          onClick={() => removeGoal(index)}
                        >
                          <Trash2 aria-hidden />
                        </button>
                      </div>
                    ))}
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
                            <td><span className="material-cell"><AssetImage src={item.image_url} alt={`${item.material_name}材料图标`} /><span>{item.material_name}</span></span></td>
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
                {!gap && <button className="primary-button mt-5 w-full justify-center" disabled={!goals.length || busy === "gap"} onClick={calculate}>{busy === "gap" ? "正在复核…" : "合并计算材料缺口"}</button>}
              </div>
            </section>

            <aside className="space-y-6">
              <div className="mission-summary">
                <p className="eyebrow text-teal-700">MISSION BRIEF</p>
                <h2>{goals.length ? `${goals[0].character.name_zh_cn}${goals.length > 1 ? ` 等 ${goals.length} 项` : ""}` : "等待编成目标"}</h2>
                <div className="summary-metrics">
                  <span><small>技能目标</small><strong>{goals.length || "—"}</strong></span>
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
                  <label><span><CalendarDays aria-hidden />截止时间</span><input type="datetime-local" value={deadline} onChange={(e) => setDeadline(e.target.value)} /></label>
                  <label><span><Clock3 aria-hidden />每日可用分钟</span><input type="number" min={1} value={dailyMinutes} onChange={(e) => setDailyMinutes(Number(e.target.value))} /></label>
                  <label>单次刷取分钟<input type="number" min={1} value={minutesPerRun} onChange={(e) => setMinutesPerRun(Number(e.target.value))} /></label>
                </div>
                <button className="primary-button mt-5 w-full justify-center" disabled={!gap || busy === "plan"} onClick={createPlan}>
                  {busy === "plan" ? "规划与验证中…" : "生成受约束路线"}
                </button>
              </div>

              {plan && (
                <div className="panel route-result">
                  <div className="flex items-start justify-between gap-4">
                    <div><p className="eyebrow">ROUTE RESULT</p><h2>任务路线已生成</h2></div>
                    <StatusPill status={plan.status} />
                  </div>
                  <div className="dataset-line">
                    <Database aria-hidden />
                    <span>数据 {plan.dataset_version ?? "无版本"} · {plan.candidate_scope}</span>
                    <small>
                      {plan.dataset_license_status === "unverified-local-only"
                        ? "本地验证数据，不随项目再分发"
                        : plan.dataset_license_status ?? "许可状态未知"}
                      {" · "}准入样本 ≥ {plan.minimum_sample_runs?.toLocaleString() ?? "—"}
                    </small>
                  </div>
                  <div className="solver-strip">
                    <span><small>求解器</small><strong>{plan.solver}</strong></span>
                    <span><small>结论</small><strong>{plan.optimality === "local_optimal" ? "固定候选集局部最优" : plan.optimality}</strong></span>
                    <span><small>搜索节点</small><strong>{plan.search_nodes.toLocaleString()}</strong></span>
                  </div>
                  <div className="route-steps">
                    {plan.steps.length ? plan.steps.map((step, index) => (
                      <div className="route-step" key={step.quest_id}>
                        <span>{String(index + 1).padStart(2, "0")}</span>
                        <AssetImage src={step.image_url} alt={`${step.quest_name}关卡图标`} />
                        <div><strong>{step.quest_name}</strong><small>关卡 {step.quest_id} · 样本 {step.sample_runs.toLocaleString()}</small></div>
                        <b>{step.runs} 次</b>
                      </div>
                    )) : <p className="text-sm text-slate-600">当前候选集中没有可验证路线。</p>}
                  </div>
                  <div className="ap-meter"><span style={{ width: `${Math.min(100, (plan.total_ap / Math.max(1, plan.available_ap)) * 100)}%` }} /></div>
                  <div className="flex justify-between text-sm"><span>预计消耗 {plan.total_ap} AP</span><span>可用 {plan.available_ap} AP</span></div>
                  <button className="secondary-button mt-4 w-full justify-center" onClick={() => { setView("trace"); loadTrace("trace"); }}>
                    <Activity aria-hidden />查看本次 Trace
                  </button>
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
