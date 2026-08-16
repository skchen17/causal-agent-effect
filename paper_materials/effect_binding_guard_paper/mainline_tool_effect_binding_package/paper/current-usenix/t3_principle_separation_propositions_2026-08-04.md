# T3 原则分离命题草稿（2026-08-04）

状态：**草稿**（供 PM 核实后收录）。纯构造性理论，无 GPU、无新实验数字。
依据：`improvement_whitepaper_2026-08-03.md` §1 T3；`window_execution_decision_2026-08-04.md` §2c（T3 最先砍，本轮做）。目标：把 theory_proof_audit 的 Novelty Boundary（"不是 least-privilege 的 rename"）从定性声明升级为**可构造分离证据**，正面回应"close to argument-provenance and contract work"。
相容性：全部引用 `security_analysis.tex` / `appendix/formal_proofs.tex` 已有定义与命题；正文未改动。
反例族锚定冻结数据：E2/有限域判定（只读）。

---

## 0. 两原则的精确化（沿用现有形式化，不引入新语义）

- **least-privilege（LP）**：monitor 为每次请求放行的授权范围不超过完成任务所必需的最小权限。在 `sec:security-analysis` 的模型里，LP 约束的是 **bound 的选择**（\(B\in\mathcal{B}\) 的实例化范围），不约束效果表示 \(\rho_E\)。
- **complete-mediation（CM）**：每个外部 effectful transition 之前必须有 guard 决策——即义务 **O3**（"Every externally effectful transition requires a preceding guard decision"）。
- **表示充分性**：`def:authorization-equivalence` / `def:joint-authorization-sufficiency`。\(\rho_E\) 保授权等价类 ⟺ \(\rho_E(u){=}\rho_E(v)\Rightarrow u\equiv_{\mathcal{B}}v\)（对 \(u,v\in D\)）。

观察（分离论证的核心）：**LP 与 CM 分别约束"给多少权限"与"何时检查"，都不约束"基于什么表示检查"**。表示层出现的信息丢失无法由"权限最小 + 全检查"挽回——这是 `thm:representation-insufficiency` 与 `prop:evidence-refinement` 注记（"complete mediation over an unsound representation remains subject to Theorem representation-insufficiency"，`formal_proofs.tex` Scope of the proofs）的直接推论。

---

## 1. 命题 (i)：两原则不蕴含安全

### 命题 T3.1（原则分离：effect-side）

```latex
\begin{proposition}[Least privilege and complete mediation do not imply safety]
\label{prop:principle-separation-effects}
Let $D$ be a finite instance domain and let $\rho_E$ be a monitor's
effect-side representation.  Suppose the monitor satisfies
least-privilege (bounds instantiate only the minimum necessary
authority) and complete mediation (every externally effectful
transition has a preceding guard decision, obligation O3).  If
$\rho_E$ is not authorization-sufficient on $D$---in particular, if
there exist $u,v\in D$ with
$\rho_E(u)=\rho_E(v)$ and some $B\in\mathcal{B}$ with
$I_B(u)\neq I_B(v)$---then the monitor cannot be both sound and
permissive on $D$.  It must either allow the unauthorized context or
withhold the authorized one.
\end{proposition}
```

**证明要点**：
1. 由不充分性取 \(u,v\in D\)，\(\rho_E(u){=}\rho_E(v)\)，无妨 \(I_B(u)=1,\ I_B(v)=0\)（对某 \(B\in\mathcal{B}\)）。
2. 在共同 authority 视图（同一 \(B\) 的完整视图）下，联合视图 \(R(u)=R(v)\) 而 \(I(u)\neq I(v)\)。
3. LP/CM 不影响决策面的表示层：任何满足两原则的确定性 monitor \(M\) 仍只是 \(R\) 的函数。由 `thm:representation-insufficiency`（附录完整证明），\(M\) 在 \(R(u)=R(v)\) 上必须返回同一决策；返回 \(\Allow\) 在 \(v\) 上违反 soundness，返回 \(\Deny/\Abstain\) 在 \(u\) 上违反 permissiveness。
4. 结论：违反 soundness 的放行（不安全）或假拒/abstain（permissiveness 损失，`prop:ambiguous-cell` 的下界）；二选一不可回避。∎

**与 Compound-effect binding 的关系**：命题 T3.1 是 `cor:compound-effect-binding` 的**两原则化显式**——该推论已展示"表示合并 + 授权不等价"的效果对迫使 monitor 二选一；T3.1 进一步说明，**即使 monitor 满足 LP+CM，该二选一依然存在**。LP+CM 是 `thm:single-commit` 安全保证的必要义务（O3）与权限边界义务，但**不是**表示充分性的替代品。

### 反例族（共享 effect 签名、授权不等价、两原则下无法分离）

构造模板：取两个调用 \(u,v\)，它们执行同一效果签名（同一 effect label + resource + operation），但某个授权相关属性不同；monitor 的表示 \(\rho_E\) 丢弃该属性。

实例（日历邀请，锚定 `sec:security-analysis` 的 motivating case 与 E2 判定）：
- \(u\)：`add_participant(calendar event 6, target=internal@example.com)` —— 授权等价类：\(I_B(u)=1\)（\(B\) 含内部成员）。
- \(v\)：`add_participant(calendar event 6, target=external@example.com)` —— \(I_B(v)=0\)（同一 \(B\) 不含外部成员）。
- \(\rho_E\) 丢弃 `target`（subject 属性）：\(\rho_E(u)=\rho_E(v)\)。

则任何基于 \(\rho_E\) 的 monitor：
- 满足 **LP**：\(B\) 是完成"添加内部成员"任务的最小权限界；
- 满足 **CM**（O3）：对 \(u,v\) 均执行了前置 guard 决策；
- 仍无法分离 \(u,v\)：放行则放行了未授权的 `external@example.com`（不安全）；拒绝则假拒了授权的 `internal@example.com`。

**冻结数据支撑（只读，不预填新数字）**：该反例族正是 E2 在 power-set 族下删除 subject/date/recurrence 等 qualifier 产生的 separating-pair 结构（`results/policy-family-sensitivity/policy-family-sensitivity-report.md`：power_set 行 date/subject/recurrence 各 16 对、payload 8 对、visibility 4 对）。也就是说：**"丢弃授权相关属性的两原则 monitor 无法分离授权不等价对"在 56-call 冻结域上已被 E2 判定实例化**（118 对公共表示、0 对 typed 表示）。论文正文引用时须使用 E2 已发布表格与 claim boundary，不另行预填数字。

---

## 2. 命题 (ii)：两原则不蕴含 atom 表示

### 命题 T3.2（whole-call 充分表示存在）

```latex
\begin{proposition}[Existence of authorization-sufficient whole-call representations]
\label{prop:whole-call-sufficient}
For every finite domain $D\subseteq\mathcal{U}$, the map
\[
  \rho_W(u)=[u]_{\equiv_{\mathcal{B}}}
\]
(a canonical identifier of the authorization-equivalence class) is an
authorization-sufficient representation on $D$, and it is a
whole-call representation: a single token per context, not a sequence
of atom instances.  Consequently, least privilege and complete
mediation do not imply that an atom-level representation is required
for sound enforcement.
\end{proposition}
```

**证明要点**：
1. \(\rho_W(u){=}\rho_W(v)\) ⟺ \(u\equiv_{\mathcal{B}}v\)，由 `def:authorization-equivalence` 得 \(I_B(u)=I_B(v)\ \forall B\)。故 \(\rho_W\) 授权充分（`def:authorization-equivalence` 的充分性定义逐字满足）。
2. \(\rho_W\) 的输出是每个 context 一个类标识（单个 token），不是 effect-instance 序列——即 whole-call 表示。
3. 由 `prop:authorization-quotient`，\(Q(D)\) 是最粗的充分表示且任何充分表示细化它；\(\rho_W\) 的 cells 恰为 quotient classes，是最粗充分表示的规范实现。
4. 结合命题 T3.1：LP+CM 不蕴含安全（表示不充分时），也不蕴含"必须以 atom 表示"（\(\rho_W\) 反例）。atom 表示是充分表示家族中的**工程选择**（可由有限验证近似、T1 收敛、E2 多族实证），不是逻辑必然。∎

**引用锚点**：`sec:security-analysis` 已声明 "They do not say that every whole-call monitor is insufficient: a whole-call representation that refines all authorization-equivalence classes would satisfy the definition"；`theory_proof_audit.md` Novelty Boundary 同句。T3.2 把该声明从"指出可能性"升级为**构造性存在命题**（映射到 quotient class 标识），并显式给出"两原则不蕴含 atom"的结论。

**边界（防反噬）**：\(\rho_W\) 的存在性不承诺其**可计算性**——它需要 oracle 判定授权等价（这正是注册验证 `thm:finite-adequacy` + T1 收敛替代的工程对象）。T3.2 的论证对象是"逻辑蕴含关系"（两原则 → atom？否），不是"存在实用的 whole-call monitor"。

---

## 3. related_work 对照段衔接建议（不修改正文）

### 3.1 现状

`related_work.tex` "Authorization, effects, and contracts" 段列举 Progent/MiniScope/ClawGuard/ScopeGate/SecureClaw/commit-time authorization 与 PACT/AuthGraph，主张"we test whether the value presented there separates authorization-relevant effects"。Novelty 边界目前仅以定性句（theory_proof_audit.md）与 `prop:authorization-quotient` 支撑。

### 3.2 建议对照句（草稿，写入正文时供 PM 定稿）

在 "Authorization, effects, and contracts" 段末尾追加 2–3 句：

> Least privilege and complete mediation constrain the scope and timing of enforcement, not the representation on which it operates. Proposition~\ref{prop:principle-separation-effects} constructs monitors that satisfy both principles yet remain unsafe whenever the effect-side representation merges authorization-inequivalent calls; Proposition~\ref{prop:whole-call-sufficient} exhibits an authorization-sufficient whole-call representation, so the two principles do not imply atom-level binding. The binding question is therefore not a relabeling of least privilege or of argument provenance: it is a property of the representation itself.

### 3.3 论证收益

- **可构造分离证据**：把"不是 rename"从定性升级为两个可引用命题（T3.1 构造反例 monitor；T3.2 构造反例表示），正面回应"close to argument-provenance and contract work"型审稿。
- **与 related_work 既有句互补**：现有句 "We build on complete mediation, capabilities, confused-deputy analysis..."（Saltzer/confused deputy 系）→ 新增句明确"我们构建在其上，但目标命题是它们不覆盖的表示层"。

---

## 4. 与现有形式化的相容性核对

- `def:authorization-equivalence` / `def:joint-authorization-sufficiency`：T3.1/T3.2 全程沿用。✓
- `thm:representation-insufficiency`：T3.1 证明的骨架（附录已有完整证明）。✓
- `cor:compound-effect-binding`：T3.1 是其两原则化显式，无冲突。✓
- `prop:authorization-quotient`：T3.2 的充分性直接由其"最粗充分表示"结论导出。✓
- `prop:ambiguous-cell`：T3.1 的 permissiveness 侧失败模式即其下界。✓
- O1–O5：仅引用 O3（complete-mediation）与 `thm:single-commit` 的义务结构；T3.1 不否认 confinement 在表示充分时的成立（`thm:single-commit` 前提含 O1 抽象 soundness），只指出两原则 ≠ 表示充分。✓
- E2 冻结报告：反例族锚定其 separating-pair 判定与 claim boundary，未预填新数字。✓
- 一致性声明：与 `theory_proof_audit.md` Novelty Boundary（whole-call 充分性声明）逐字兼容，并补足构造。✓

**不承诺清单**：\(\rho_W\) 的可计算实现；两原则之外其他义务组合下的安全性；开放域表示充分性。
