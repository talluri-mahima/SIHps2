import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  Building2,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Clock3,
  FileCheck2,
  FileText,
  Fingerprint,
  FolderOpen,
  Layers3,
  LayoutDashboard,
  Link2,
  LoaderCircle,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Upload,
  Wallet,
  X,
} from "lucide-react";
import "./styles.css";

type Fact = {
  id: string;
  document_id: string;
  key: string;
  raw: string;
  value: unknown;
  page: number;
  bbox: number[];
  revision: number;
  confirmed_by: string | null;
  engine: string;
};
type Doc = {
  id: string;
  kind: string;
  filename: string;
  status: string;
  version: number;
  sha256: string;
  pages: number;
  fields: Fact[];
  source_status: string;
  source_mode: string;
};
type Finding = {
  id: string;
  title: string;
  explanation: string;
  rule_id: string;
  state: string;
  version: number;
  module: string;
  reason: string;
  required_action: string;
  evidence: {
    document_id: string;
    field_id: string;
    page: number;
    bbox: number[];
  }[];
};
type Evaluation = {
  id: string;
  stale: boolean;
  findings: Finding[];
  coverage: {
    building: string;
    floor: string;
    occupancy: string;
    fire: string;
  }[];
  manifest_hash: string;
  created_at: string;
};
type Detail = {
  id: string;
  name: string;
  category: string;
  academic_year: string;
  evaluation_date: string;
  revision: number;
  synthetic: boolean;
  checklist: { kind: string; received: boolean }[];
  documents: Doc[];
  evaluation: Evaluation | null;
  document_kinds: string[];
};
type User = { name: string; role: string; tenant: string };
type Summary = { id: string; name: string; category: string };
type Audit = {
  integrity: boolean;
  events: {
    id: number;
    action: string;
    actor: string;
    at: string;
    detail: unknown;
    hash: string;
  }[];
};
type Page =
  | "Overview"
  | "Evidence"
  | "Infrastructure"
  | "Financial evidence"
  | "Findings"
  | "Audit trail";
const nav = [
  { name: "Overview", icon: LayoutDashboard },
  { name: "Evidence", icon: FolderOpen },
  { name: "Infrastructure", icon: Building2 },
  { name: "Financial evidence", icon: Wallet },
  { name: "Findings", icon: FileCheck2 },
  { name: "Audit trail", icon: Fingerprint },
] as const;
const pretty = (value: string) =>
  value
    .toLowerCase()
    .replaceAll("_", " ")
    .replace(/\b\w/g, (s) => s.toUpperCase());
const show = (v: unknown): string =>
  Array.isArray(v) ? v.join(", ") : String(v);
async function api<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  const response = await fetch("/v1" + url, {
    ...options,
    headers,
    credentials: "same-origin",
  });
  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({ detail: "Request failed" }));
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : JSON.stringify(body.detail),
    );
  }
  return response.json();
}
function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  return <span className={"badge " + tone}>{children}</span>;
}
function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div className="empty">
      <CircleHelp size={25} />
      <p>{children}</p>
    </div>
  );
}

function App() {
  const [user, setUser] = useState<User | null>(null),
    [list, setList] = useState<Summary[]>([]),
    [active, setActive] = useState("");
  const [data, setData] = useState<Detail | null>(null),
    [page, setPage] = useState<Page>("Overview"),
    [docId, setDocId] = useState(""),
    [fieldId, setFieldId] = useState("");
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [toast, setToast] = useState(""),
    [audit, setAudit] = useState<Audit | null>(null);
  const [modal, setModal] = useState<null | "upload" | "create" | "source">(
      null,
    ),
    [finding, setFinding] = useState<Finding | null>(null),
    [action, setAction] = useState("CONFIRM");
  const [reason, setReason] = useState(""),
    [editing, setEditing] = useState<Fact | null>(null),
    [editValue, setEditValue] = useState("");
  const [search, setSearch] = useState("");
  const isOfficer = user?.role === "OFFICER",
    isApplicant = user?.role === "SUBMITTER";
  const doc = data?.documents.find((d) => d.id === docId) || data?.documents[0];
  const field = doc?.fields.find((f) => f.id === fieldId) || doc?.fields[0];
  const findings = data?.evaluation?.findings || [];
  const unconfirmed =
    data?.documents.reduce(
      (n, d) => n + d.fields.filter((f) => !f.confirmed_by).length,
      0,
    ) || 0;
  const received = data?.checklist.filter((c) => c.received).length || 0;
  async function refresh(id = active) {
    if (!id) return;
    const result = await api<Detail>("/applications/" + id);
    setData(result);
    if (page === "Audit trail")
      setAudit(await api<Audit>("/applications/" + id + "/audit"));
  }
  async function loadApplications() {
    const result = await api<Summary[]>("/applications");
    setList(result);
    setActive((old) =>
      result.some((a) => a.id === old) ? old : result[0]?.id || "",
    );
  }
  async function perform(work: () => Promise<void>, message = "") {
    setError("");
    setBusy(true);
    try {
      await work();
      if (message) setToast(message);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function login(persona: string) {
    await perform(async () => {
      setUser(await api<User>("/dev/session/" + persona, { method: "POST" }));
      setData(null);
      await loadApplications();
    });
  }
  useEffect(() => {
    api<User>("/auth/me")
      .then((u) => {
        setUser(u);
        void loadApplications();
      })
      .catch(() => {});
  }, []);
  useEffect(() => {
    if (active) void perform(() => refresh(active));
  }, [active]);
  useEffect(() => {
    if (page === "Audit trail" && active)
      api<Audit>("/applications/" + active + "/audit")
        .then(setAudit)
        .catch((e) => setError(e.message));
  }, [page, active, data?.revision]);
  useEffect(() => {
    if (
      !data?.documents.some((d) => ["QUEUED", "PROCESSING"].includes(d.status))
    )
      return;
    const timer = setInterval(() => {
      void refresh();
    }, 1500);
    return () => clearInterval(timer);
  }, [data?.documents, active]);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(""), 5000);
    return () => clearTimeout(t);
  }, [toast]);
  useEffect(() => {
    if (!modal && !finding && !editing) return;
    const previous = document.activeElement as HTMLElement | null;
    const dialog = document.querySelector(".modal");
    const targets = () =>
      Array.from(
        dialog?.querySelectorAll<HTMLElement>(
          "button:not(:disabled),input,textarea,select,a[href]",
        ) || [],
      );
    targets()[0]?.focus();
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) {
        setModal(null);
        setFinding(null);
        setEditing(null);
      }
      if (event.key === "Tab") {
        const items = targets();
        const first = items[0],
          last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", handler);
    return () => {
      document.removeEventListener("keydown", handler);
      previous?.focus();
    };
  }, [modal, finding, editing, busy]);
  const openEvidence = (documentId: string, factId = "") => {
    setDocId(documentId);
    setFieldId(factId);
    setPage("Evidence");
  };
  async function confirmDocument() {
    if (!doc) return;
    await perform(async () => {
      for (const f of doc.fields.filter((f) => !f.confirmed_by)) {
        await api("/fields/" + f.id, {
          method: "PATCH",
          headers: { "If-Match": String(f.revision) },
          body: JSON.stringify({
            raw_value: show(f.value),
            reason:
              "Reviewed against the displayed synthetic original document.",
          }),
        });
      }
      await refresh();
    }, "Facts confirmed. Run checks to use the latest evidence.");
  }
  async function runChecks() {
    await perform(async () => {
      await api("/applications/" + active + "/evaluations", { method: "POST" });
      await refresh();
    }, "Evidence checks completed. Findings require human review.");
  }
  async function downloadReport() {
    await perform(async () => {
      const result = await api<unknown>(
        "/applications/" + active + "/exports",
        { method: "POST" },
      );
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(result, null, 2)], {
          type: "application/json",
        }),
      );
      const a = document.createElement("a");
      a.href = url;
      a.download = "synthetic-review-report.json";
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }, "Demonstration review report exported.");
  }
  if (!user)
    return (
      <main className="login-page">
        <div className="login-brand">
          <Layers3 size={29} /> EVIDENCE WORKBENCH <span>SIH 26261</span>
        </div>
        <div className="login-content">
          <Badge tone="mint">LOCAL DEVELOPMENT WORKSPACE</Badge>
          <h1>
            Every claim.
            <br />
            <em>Connected to evidence.</em>
          </h1>
          <p>
            A workspace for application scrutiny, infrastructure coverage and
            financial evidence reconciliation.
          </p>
          <div className="login-box">
            <h2>Explore the working foundation</h2>
            <p>Choose a role to use the synthetic demonstration.</p>
            {[
              {
                id: "officer",
                name: "Scrutiny officer",
                desc: "Inspect evidence, run checks and review findings",
                icon: ShieldCheck,
              },
              {
                id: "institution",
                name: "Institution applicant",
                desc: "Create applications and submit evidence",
                icon: Building2,
              },
              {
                id: "auditor",
                name: "Independent auditor",
                desc: "Inspect evidence and the read-only audit trail",
                icon: Fingerprint,
              },
            ].map((p) => (
              <button
                className="persona"
                key={p.id}
                disabled={busy}
                onClick={() => void login(p.id)}
              >
                <p.icon size={23} />
                <span>
                  <strong>{p.name}</strong>
                  <small>{p.desc}</small>
                </span>
                <ArrowRight size={20} />
              </button>
            ))}
          </div>
          <p className="login-note">
            Synthetic records · Draft consistency rules · No government
            connection
          </p>
          {error && (
            <div role="alert" className="alert error">
              {error}
            </div>
          )}
        </div>
        <div className="login-art">
          <div className="orbit one" />
          <div className="orbit two" />
          <div className="art-card">
            <span className="tiny-label">DOCUMENTARY COVERAGE</span>
            <h3>
              The right evidence.
              <br />
              For the exact claim.
            </h3>
            <div className="art-floor">
              <Building2 />
              Block C <Badge tone="mint">Scope mapped</Badge>
            </div>
            {[
              ["Second floor", "Review needed"],
              ["First floor", "Supported"],
              ["Ground floor", "Supported"],
            ].map(([n, s]) => (
              <div className="floor" key={n}>
                <span>{n}</span>
                <span className={s === "Supported" ? "supported" : "review"}>
                  {s === "Supported" ? (
                    <Check size={15} />
                  ) : (
                    <Clock3 size={15} />
                  )}{" "}
                  {s}
                </span>
              </div>
            ))}
            <div className="art-foot">
              <Link2 size={14} /> Original → Accepted fact → Review finding
            </div>
          </div>
          <div className="floating-note">
            <Fingerprint size={19} />
            <span>
              Traceable by design
              <small>Document · Page · Fact · Rule · Reviewer</small>
            </span>
          </div>
        </div>
      </main>
    );
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setPage("Overview");
          }}
        >
          <div className="brand-icon">
            <Layers3 size={23} />
          </div>
          <span>
            Evidence<span className="brand-sub">WORKBENCH / SIH 26261</span>
          </span>
        </a>
        <div className="workspace-label">SCRUTINY WORKSPACE</div>
        <nav aria-label="Workspace">
          {nav.map((n) => (
            <button
              key={n.name}
              aria-label={n.name}
              className={page === n.name ? "nav-item selected" : "nav-item"}
              onClick={() => setPage(n.name)}
            >
              <n.icon size={19} />
              <span>{n.name}</span>
              {n.name === "Findings" && findings.length > 0 && (
                <span className="nav-count">{findings.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="rule-status">
            <ShieldCheck size={19} />
            <span>
              Evidence, before decisions
              <small>Human review remains essential</small>
            </span>
          </div>
          <div className="profile">
            <div className="avatar">{user.name[0]}</div>
            <div>
              <strong>{user.name}</strong>
              <small>{pretty(user.role)}</small>
            </div>
          </div>
          <label className="switch-role">
            Demo role
            <select
              value={
                user.role === "OFFICER"
                  ? "officer"
                  : user.role === "AUDITOR"
                    ? "auditor"
                    : "institution"
              }
              onChange={(e) => void login(e.target.value)}
              disabled={busy}
            >
              <option value="officer">Scrutiny officer</option>
              <option value="institution">Institution applicant</option>
              <option value="auditor">Read-only auditor</option>
            </select>
          </label>
        </div>
      </aside>
      <div className="main-wrap">
        <header className="topbar">
          <div className="breadcrumbs">
            Workspace <ChevronRight size={13} /> <span>{page}</span>
          </div>
          <div className="top-right">
            <span className="status-dot" /> Local workspace{" "}
            <span className="divider" />
            <Badge tone="amber">Synthetic demonstration</Badge>
            <label className="mobile-role">
              Role
              <select
                aria-label="Demo role"
                value={
                  user.role === "OFFICER"
                    ? "officer"
                    : user.role === "AUDITOR"
                      ? "auditor"
                      : "institution"
                }
                onChange={(e) => void login(e.target.value)}
                disabled={busy}
              >
                <option value="officer">Officer</option>
                <option value="institution">Applicant</option>
                <option value="auditor">Auditor</option>
              </select>
            </label>
          </div>
        </header>
        <main className="main-content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                APPLICATION SCRUTINY · {data?.academic_year || "2026–27"}
              </div>
              <h1>{page === "Overview" ? "Application overview" : page}</h1>
              <p>
                {page === "Overview"
                  ? "See what is submitted, what it supports, and what needs a closer look."
                  : page === "Evidence"
                    ? "Inspect original documents and confirm the facts used in checks."
                    : page === "Infrastructure"
                      ? "Match claimed floors to the scope established by each document."
                      : page === "Financial evidence"
                        ? "Reconcile instrument identity, funding claims and encumbrances."
                        : page === "Findings"
                          ? "Review evidence gaps before they become confirmed observations."
                          : "A durable record of evidence, checks and human review."}
              </p>
            </div>
            <div className="heading-actions">
              {isApplicant ? (
                <button className="primary" onClick={() => setModal("create")}>
                  <Plus size={17} />
                  New application
                </button>
              ) : (
                <button
                  className="secondary"
                  onClick={() => void perform(() => refresh())}
                  disabled={busy}
                >
                  <RefreshCw size={16} className={busy ? "spin" : ""} />
                  Refresh
                </button>
              )}
              {isOfficer && (
                <button
                  className="primary"
                  disabled={busy || !data}
                  onClick={() => void runChecks()}
                >
                  {busy ? (
                    <LoaderCircle size={17} className="spin" />
                  ) : (
                    <ShieldCheck size={17} />
                  )}
                  Run evidence checks
                </button>
              )}
            </div>
          </div>
          {error && (
            <div role="alert" className="alert error">
              <span>{error}</span>
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          {toast && (
            <div role="status" className="toast">
              <CheckCheck size={17} />
              {toast}
            </div>
          )}
          <section className="application-bar">
            <div className="institution-icon">
              <Building2 size={23} />
            </div>
            <div className="app-select">
              <label htmlFor="application-select">CURRENT APPLICATION</label>
              <select
                id="application-select"
                value={active}
                onChange={(e) => {
                  setActive(e.target.value);
                  setDocId("");
                  setFieldId("");
                }}
              >
                {list.map((a) => (
                  <option value={a.id} key={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="app-meta">
              <span>
                {data?.category === "EOA"
                  ? "Extension of Approval"
                  : "New institution"}
              </span>
              <small>Engineering & Technology · UG</small>
            </div>
            <div className="app-meta">
              <span>{data?.evaluation_date || "—"}</span>
              <small>Evaluation date</small>
            </div>
            <Badge tone="amber">Policy review pending</Badge>
          </section>
          {data?.evaluation?.stale && (
            <div className="alert warning">
              <Clock3 size={17} />
              <span>
                Evidence changed since the last evaluation. Run checks again
                before confirming findings or exporting.
              </span>
            </div>
          )}
          {!data ? (
            <Empty>
              {busy
                ? "Loading your workspace…"
                : "No application selected. Create a synthetic application to begin."}
            </Empty>
          ) : (
            <>
              {page === "Overview" && (
                <>
                  <div className="stats">
                    <Stat
                      label="CHECKLIST EVIDENCE"
                      value={`${received} / ${data.checklist.length}`}
                      sub="Expected document types received"
                      icon={<FolderOpen size={19} />}
                    />
                    <Stat
                      label="FACTS TO CONFIRM"
                      value={String(unconfirmed)}
                      sub="Critical facts awaiting human review"
                      icon={<Search size={19} />}
                      amber={unconfirmed > 0}
                    />
                    <Stat
                      label="REVIEW FINDINGS"
                      value={
                        data.evaluation
                          ? String(
                              findings.filter(
                                (f) =>
                                  !["RESOLVED", "DISMISSED"].includes(f.state),
                              ).length,
                            )
                          : "—"
                      }
                      sub={
                        data.evaluation
                          ? "From the latest evidence evaluation"
                          : "Run checks after confirming facts"
                      }
                      icon={<FileCheck2 size={19} />}
                    />
                    <Stat
                      label="SOURCE VERIFICATION"
                      value={String(
                        data.documents.filter(
                          (d) =>
                            d.source_status === "VERIFIED" &&
                            d.source_mode === "MANUAL",
                        ).length,
                      )}
                      sub="Manual attestations · no live sources"
                      icon={<ShieldCheck size={19} />}
                    />
                  </div>
                  <div className="overview-grid">
                    <section className="panel">
                      <PanelTitle
                        title="Evidence readiness"
                        subtitle="The document set for this application context"
                        action={
                          <button
                            className="text-button"
                            onClick={() => setPage("Evidence")}
                          >
                            View evidence <ArrowUpRight size={15} />
                          </button>
                        }
                      />
                      <div className="checklist">
                        {data.checklist.map((c, i) => (
                          <div className="checklist-row" key={c.kind}>
                            <span
                              className={
                                "check-circle " + (c.received ? "done" : "")
                              }
                            >
                              {c.received ? (
                                <Check size={15} />
                              ) : (
                                String(i + 1).padStart(2, "0")
                              )}
                            </span>
                            <div>
                              <strong>{pretty(c.kind)}</strong>
                              <small>
                                {c.received
                                  ? "Received · inspect extracted facts"
                                  : "Awaiting submission"}
                              </small>
                            </div>
                            <Badge tone={c.received ? "mint" : "neutral"}>
                              {c.received ? "Received" : "Missing"}
                            </Badge>
                          </div>
                        ))}
                      </div>
                      <div className="panel-footer">
                        <span>Checklist basis: demonstration workflow</span>
                        <Badge>Draft pack v0.1.0</Badge>
                      </div>
                    </section>
                    <section className="panel focus-panel">
                      <PanelTitle
                        title="From document to supported claim"
                        subtitle="Two focused evidence-reconciliation modules"
                      />
                      <button
                        className="module-card"
                        onClick={() => setPage("Infrastructure")}
                      >
                        <div className="module-icon">
                          <Building2 size={25} />
                        </div>
                        <div>
                          <div className="module-label">SCOPEGUARD</div>
                          <h3>Does the certificate cover the claim?</h3>
                          <p>
                            Trace occupancy and fire evidence to the exact
                            building and floor.
                          </p>
                          <span>
                            Inspect infrastructure <ArrowRight size={15} />
                          </span>
                        </div>
                      </button>
                      <button
                        className="module-card finance"
                        onClick={() => setPage("Financial evidence")}
                      >
                        <div className="module-icon">
                          <Wallet size={25} />
                        </div>
                        <div>
                          <div className="module-label">HESTIA</div>
                          <h3>Is the funding evidence consistent?</h3>
                          <p>
                            Link the same deposit across a DPR, FDR advice and
                            lien evidence.
                          </p>
                          <span>
                            Reconcile financial evidence{" "}
                            <ArrowRight size={15} />
                          </span>
                        </div>
                      </button>
                    </section>
                  </div>
                  <section className="panel workflow">
                    <div>
                      <span className="tiny-label">YOUR NEXT STEP</span>
                      <h3>
                        {unconfirmed
                          ? "Review and confirm extracted facts"
                          : data.evaluation
                            ? "Inspect the latest findings"
                            : "Run the first evidence evaluation"}
                      </h3>
                      <p>
                        {unconfirmed
                          ? "Open each original and confirm its facts. Unconfirmed data cannot establish a supported claim."
                          : "Findings are review leads. Only an authorized reviewer can confirm an observation."}
                      </p>
                    </div>
                    <button
                      className="secondary"
                      onClick={() =>
                        setPage(unconfirmed ? "Evidence" : "Findings")
                      }
                    >
                      {unconfirmed ? "Review evidence" : "Open findings"}
                      <ArrowRight size={16} />
                    </button>
                  </section>
                </>
              )}
              {page === "Evidence" && (
                <div className="evidence-layout">
                  <section className="panel document-list">
                    <PanelTitle
                      title="Document inventory"
                      subtitle={`${data.documents.length} current versions`}
                      action={
                        isApplicant ? (
                          <button
                            className="icon-button"
                            aria-label="Upload evidence"
                            onClick={() => setModal("upload")}
                          >
                            <Plus size={19} />
                          </button>
                        ) : undefined
                      }
                    />
                    {data.documents.map((d) => (
                      <button
                        key={d.id}
                        onClick={() => {
                          setDocId(d.id);
                          setFieldId("");
                        }}
                        className={
                          "doc-row " + (doc?.id === d.id ? "active" : "")
                        }
                      >
                        <FileText size={21} />
                        <span>
                          <strong>{pretty(d.kind)}</strong>
                          <small>
                            Version {d.version} · {d.fields.length} facts
                          </small>
                        </span>
                        <span
                          className={
                            "mini-dot " +
                            (d.fields.length &&
                            d.fields.every((f) => f.confirmed_by)
                              ? "green"
                              : "orange")
                          }
                        />
                      </button>
                    ))}
                    {isApplicant && (
                      <button
                        className="upload-dashed"
                        onClick={() => setModal("upload")}
                      >
                        <Upload size={18} />
                        Add / replace evidence
                      </button>
                    )}
                    <div className="inventory-note">
                      <Fingerprint size={18} />
                      <p>
                        Originals are preserved. Replacement uploads create a
                        new version.
                      </p>
                    </div>
                  </section>
                  <section className="panel evidence-detail">
                    {doc ? (
                      <>
                        <PanelTitle
                          title={pretty(doc.kind)}
                          subtitle={`Version ${doc.version} · ${doc.pages} page${doc.pages === 1 ? "" : "s"} · ${pretty(doc.status)}`}
                          action={
                            <a
                              className="text-button"
                              href={"/v1/documents/" + doc.id + "/original"}
                              target="_blank"
                              rel="noreferrer"
                            >
                              Open original
                              <ArrowUpRight size={15} />
                            </a>
                          }
                        />
                        <div className="evidence-body">
                          <div className="page-view">
                            <div className="page-toolbar">
                              <FileText size={14} />
                              Original evidence{" "}
                              <span>Page {field?.page || 1}</span>
                            </div>
                            {doc.status === "EXTRACTED" ? (
                              <div className="paper">
                                <img
                                  src={
                                    "/v1/documents/" +
                                    doc.id +
                                    "/pages/" +
                                    (field?.page || 1)
                                  }
                                  alt={`${pretty(doc.kind)} original page ${field?.page || 1}`}
                                />
                                {field && (
                                  <div
                                    className="evidence-box"
                                    style={{
                                      left: field.bbox[0] * 100 + "%",
                                      top: field.bbox[1] * 100 + "%",
                                      width:
                                        (field.bbox[2] - field.bbox[0]) * 100 +
                                        "%",
                                      height:
                                        (field.bbox[3] - field.bbox[1]) * 100 +
                                        "%",
                                    }}
                                  />
                                )}
                              </div>
                            ) : (
                              <Empty>
                                {pretty(doc.status)}. Unsupported scans and
                                layouts require manual extraction.
                              </Empty>
                            )}
                            <div className="hash-label">
                              <Fingerprint size={12} />
                              SHA-256 {doc.sha256.slice(0, 20)}…
                            </div>
                          </div>
                          <div className="facts">
                            <div className="facts-heading">
                              <h3>Extracted facts</h3>
                              <Badge tone="amber">
                                {
                                  doc.fields.filter((f) => !f.confirmed_by)
                                    .length
                                }{" "}
                                pending
                              </Badge>
                            </div>
                            <p className="muted small">
                              Select a fact to locate its source. Confirm only
                              after reviewing the original.
                            </p>
                            {doc.fields.map((f) => (
                              <div
                                className={
                                  "fact " +
                                  (field?.id === f.id ? "focused" : "")
                                }
                                key={f.id}
                              >
                                <button
                                  className="fact-main"
                                  onClick={() => setFieldId(f.id)}
                                >
                                  <span className="fact-key">
                                    {pretty(f.key)}
                                  </span>
                                  <strong>{show(f.value)}</strong>
                                  <small>
                                    {f.confirmed_by ? (
                                      <>
                                        <Check size={12} />
                                        Reviewer confirmed
                                      </>
                                    ) : (
                                      <>
                                        <Clock3 size={12} />
                                        Unconfirmed
                                      </>
                                    )}{" "}
                                    · Page {f.page}
                                  </small>
                                </button>
                                {isOfficer && (
                                  <button
                                    className="text-button"
                                    onClick={() => {
                                      setEditing(f);
                                      setEditValue(show(f.value));
                                      setReason("");
                                    }}
                                  >
                                    {f.confirmed_by ? "Edit" : "Review"}
                                  </button>
                                )}
                              </div>
                            ))}
                            {!doc.fields.length && (
                              <Empty>
                                No supported labelled facts extracted. This
                                version cannot silently pass checks.
                              </Empty>
                            )}
                            {isOfficer &&
                              doc.fields.some((f) => !f.confirmed_by) && (
                                <button
                                  className="primary full"
                                  disabled={busy}
                                  onClick={() => void confirmDocument()}
                                >
                                  <CheckCheck size={16} />
                                  Confirm displayed document facts
                                </button>
                              )}
                            <div className="source-card">
                              <span className="tiny-label">
                                ISSUER VERIFICATION
                              </span>
                              <strong>{pretty(doc.source_status)}</strong>
                              <small>
                                Mode: {pretty(doc.source_mode)} · Separate from
                                documentary scope
                              </small>
                              {isOfficer && (
                                <button
                                  className="text-button"
                                  onClick={() => {
                                    setReason("");
                                    setModal("source");
                                  }}
                                >
                                  Record source observation
                                  <ArrowRight size={14} />
                                </button>
                              )}
                            </div>
                          </div>
                        </div>
                      </>
                    ) : (
                      <Empty>No evidence received yet.</Empty>
                    )}
                  </section>
                </div>
              )}
              {page === "Infrastructure" && (
                <>
                  <section className="module-banner">
                    <div className="module-icon">
                      <Building2 size={27} />
                    </div>
                    <div>
                      <span className="tiny-label">
                        SCOPEGUARD · DOCUMENTARY COVERAGE
                      </span>
                      <h2>Valid evidence. Precise scope.</h2>
                      <p>
                        A plan, an occupancy record and fire evidence support
                        different claims.
                      </p>
                    </div>
                    <Badge tone="mint">Building → Floor → Evidence</Badge>
                  </section>
                  <section className="panel">
                    <PanelTitle
                      title="Claim-to-evidence coverage"
                      subtitle="Supported means accepted documentary scope; it does not certify physical safety."
                    />
                    {data.evaluation?.coverage.length ? (
                      <div className="table-wrap">
                        <table>
                          <thead>
                            <tr>
                              <th>Building / claimed floor</th>
                              <th>Occupancy evidence</th>
                              <th>Fire evidence</th>
                              <th>Review context</th>
                            </tr>
                          </thead>
                          <tbody>
                            {data.evaluation.coverage.map((r) => (
                              <tr key={r.floor}>
                                <td>
                                  <div className="floor-label">
                                    <Layers3 size={18} />
                                    <span>
                                      <strong>{pretty(r.building)}</strong>
                                      <small>
                                        {r.floor === "G"
                                          ? "Ground floor"
                                          : "Floor " + r.floor}
                                      </small>
                                    </span>
                                  </div>
                                </td>
                                <td>
                                  <Badge
                                    tone={
                                      r.occupancy === "SUPPORTED"
                                        ? "mint"
                                        : "amber"
                                    }
                                  >
                                    {pretty(r.occupancy)}
                                  </Badge>
                                </td>
                                <td>
                                  <Badge
                                    tone={
                                      r.fire === "SUPPORTED" ? "mint" : "amber"
                                    }
                                  >
                                    {pretty(r.fire)}
                                  </Badge>
                                </td>
                                <td className="muted">
                                  {r.occupancy === "SUPPORTED"
                                    ? "Scope appears in accepted evidence"
                                    : "Coverage not established; request clarification"}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <Empty>
                        Confirm the room-schedule and certificate facts, then
                        run evidence checks.
                      </Empty>
                    )}
                  </section>
                  <div className="two-col">
                    {data.documents
                      .filter((d) =>
                        [
                          "ROOM_SCHEDULE",
                          "OCCUPANCY",
                          "FIRE_CERTIFICATE",
                        ].includes(d.kind),
                      )
                      .map((d) => (
                        <button
                          className="panel linked-doc"
                          key={d.id}
                          onClick={() => openEvidence(d.id)}
                        >
                          <FileText size={24} />
                          <span>
                            <strong>{pretty(d.kind)}</strong>
                            <small>
                              Version {d.version} ·{" "}
                              {d.fields.filter((f) => f.confirmed_by).length}/
                              {d.fields.length} facts confirmed
                            </small>
                          </span>
                          <ArrowUpRight size={18} />
                        </button>
                      ))}
                  </div>
                  <div className="explanation">
                    <CircleHelp size={20} />
                    <p>
                      <strong>
                        Missing scope is not proof of missing rooms.
                      </strong>{" "}
                      When a certificate omits a floor or building identity is
                      unconfirmed, the system retains “Unknown” and asks for
                      evidence.
                    </p>
                  </div>
                </>
              )}
              {page === "Financial evidence" && (
                <>
                  <section className="module-banner">
                    <div className="module-icon gold">
                      <Wallet size={27} />
                    </div>
                    <div>
                      <span className="tiny-label">
                        HESTIA · FINANCIAL RECONCILIATION
                      </span>
                      <h2>Follow the instrument, not just the amount.</h2>
                      <p>
                        Exact instrument number, holder and bank establish the
                        documentary link.
                      </p>
                    </div>
                    <Badge tone="amber">Residual availability: unknown</Badge>
                  </section>
                  <div className="two-col">
                    {data.documents
                      .filter((d) =>
                        ["DPR", "FDR_ADVICE", "LIEN_EVIDENCE"].includes(d.kind),
                      )
                      .map((d) => (
                        <section className="panel finance-doc" key={d.id}>
                          <PanelTitle
                            title={pretty(d.kind)}
                            subtitle={`Version ${d.version} · ${pretty(d.source_status)}`}
                            action={
                              <button
                                className="text-button"
                                onClick={() => openEvidence(d.id)}
                              >
                                Evidence
                                <ArrowUpRight size={15} />
                              </button>
                            }
                          />
                          <div className="finance-facts">
                            {d.fields.map((f) => (
                              <button
                                onClick={() => openEvidence(d.id, f.id)}
                                key={f.id}
                              >
                                <span>{pretty(f.key)}</span>
                                <strong>
                                  {f.key.endsWith("_INR")
                                    ? "₹ " +
                                      Number(f.value).toLocaleString("en-IN")
                                    : show(f.value)}
                                </strong>
                                <small>
                                  {f.confirmed_by
                                    ? "Confirmed fact"
                                    : "Awaiting confirmation"}
                                  <ArrowUpRight size={12} />
                                </small>
                              </button>
                            ))}
                          </div>
                        </section>
                      ))}
                  </div>
                  {!data.documents.some((d) =>
                    ["DPR", "FDR_ADVICE"].includes(d.kind),
                  ) && (
                    <Empty>
                      No financial documents received for this application.
                    </Empty>
                  )}
                  <div className="explanation">
                    <CircleHelp size={20} />
                    <p>
                      <strong>
                        Principal minus lien is not certified available funding.
                      </strong>{" "}
                      Current obligations and bank confirmation may be needed.
                      The system preserves unknown residual availability and
                      never makes a fraud allegation.
                    </p>
                  </div>
                  {findings
                    .filter((f) => f.module === "Hestia")
                    .map((f) => (
                      <FindingCard
                        key={f.id}
                        f={f}
                        onEvidence={openEvidence}
                        onReview={() => {
                          setFinding(f);
                          setAction(isApplicant ? "RESPOND" : "CONFIRM");
                          setReason("");
                        }}
                        canReview={user.role !== "AUDITOR"}
                      />
                    ))}
                </>
              )}
              {page === "Findings" && (
                <>
                  <div className="findings-toolbar">
                    <div className="search">
                      <Search size={17} />
                      <input
                        aria-label="Search findings"
                        placeholder="Search findings or rule IDs"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                      />
                    </div>
                    <span className="muted small">
                      {findings.length} observations · no automatic approval
                      decisions
                    </span>
                    {isOfficer && (
                      <button
                        className="secondary"
                        disabled={
                          busy || !data.evaluation || data.evaluation.stale
                        }
                        onClick={() => void downloadReport()}
                      >
                        <ArrowDownToLine size={16} />
                        Export confirmed observations
                      </button>
                    )}
                  </div>
                  {findings.length ? (
                    findings
                      .filter((f) =>
                        (f.title + " " + f.rule_id)
                          .toLowerCase()
                          .includes(search.toLowerCase()),
                      )
                      .map((f) => (
                        <FindingCard
                          key={f.id}
                          f={f}
                          onEvidence={openEvidence}
                          onReview={() => {
                            setFinding(f);
                            setAction(isApplicant ? "RESPOND" : "CONFIRM");
                            setReason("");
                          }}
                          canReview={user.role !== "AUDITOR"}
                        />
                      ))
                  ) : (
                    <section className="panel">
                      <Empty>
                        {data.evaluation
                          ? "No findings in the latest evaluated scope. This is not an institutional approval."
                          : "Run evidence checks to produce review observations."}
                      </Empty>
                    </section>
                  )}
                  <div className="explanation">
                    <ShieldCheck size={20} />
                    <p>
                      <strong>Draft rules, visible reasoning.</strong> Exports
                      are synthetic demonstration reports, not official AICTE
                      deficiencies. Only reviewer-confirmed current observations
                      are included.
                    </p>
                  </div>
                  {data.evaluation && (
                    <div className="manifest">
                      <Fingerprint size={17} />
                      <span>
                        Evaluation manifest{" "}
                        <code>{data.evaluation.manifest_hash}</code>
                      </span>
                      <a
                        className="text-button"
                        target="_blank"
                        rel="noreferrer"
                        href={
                          "/v1/evaluations/" + data.evaluation.id + "/manifest"
                        }
                      >
                        Inspect trace
                        <ArrowUpRight size={14} />
                      </a>
                    </div>
                  )}
                </>
              )}
              {page === "Audit trail" && (
                <section className="panel">
                  <PanelTitle
                    title="Activity and evidence history"
                    subtitle="Append-only application events with a verifiable hash chain"
                    action={
                      <Badge tone={audit?.integrity ? "mint" : "amber"}>
                        {audit?.integrity
                          ? "Chain intact"
                          : "Checking integrity"}
                      </Badge>
                    }
                  />
                  <div className="timeline">
                    {[...(audit?.events || [])].reverse().map((e) => (
                      <div className="timeline-event" key={e.id}>
                        <div className="timeline-dot">
                          <Fingerprint size={15} />
                        </div>
                        <div>
                          <strong>{pretty(e.action)}</strong>
                          <small>
                            {new Date(e.at).toLocaleString("en-IN", {
                              timeZone: "Asia/Kolkata",
                            })}{" "}
                            IST ·{" "}
                            {e.actor === "worker"
                              ? "Processing worker"
                              : e.actor === "seed"
                                ? "Synthetic seed"
                                : "Authenticated user"}
                          </small>
                          <details>
                            <summary>Inspect event record</summary>
                            <pre>{JSON.stringify(e.detail, null, 2)}</pre>
                            <code>{e.hash}</code>
                          </details>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </>
          )}
          <footer className="footer">
            <span>SIH PS 26261 · Evidence Workbench</span>
            <span>
              Development foundation · Draft rules · Synthetic records
            </span>
          </footer>
        </main>
      </div>
      {(modal || finding || editing) && (
        <div
          className="modal-backdrop"
          onClick={() => {
            if (!busy) {
              setModal(null);
              setFinding(null);
              setEditing(null);
            }
          }}
        >
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="dialog-title"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="modal-close"
              aria-label="Close dialog"
              disabled={busy}
              onClick={() => {
                setModal(null);
                setFinding(null);
                setEditing(null);
              }}
            >
              <X size={20} />
            </button>
            {modal === "upload" && (
              <>
                <h2 id="dialog-title">Submit evidence</h2>
                <p>
                  PDF only, up to 10 MB and 30 pages. Originals are retained as
                  new versions. Use synthetic data only.
                </p>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const form = new FormData(e.currentTarget);
                    void perform(async () => {
                      await api("/applications/" + active + "/documents", {
                        method: "POST",
                        headers: { "Idempotency-Key": crypto.randomUUID() },
                        body: form,
                      });
                      setModal(null);
                      await refresh();
                    }, "Evidence queued for processing.");
                  }}
                >
                  <label>
                    Document type
                    <select name="kind">
                      {data?.document_kinds.map((k) => (
                        <option key={k} value={k}>
                          {pretty(k)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Original PDF
                    <input
                      type="file"
                      name="file"
                      accept="application/pdf,.pdf"
                      required
                    />
                  </label>
                  <button className="primary full" disabled={busy}>
                    <Upload size={17} />
                    Submit document
                  </button>
                </form>
              </>
            )}
            {modal === "create" && (
              <>
                <h2 id="dialog-title">Create a synthetic application</h2>
                <p>
                  The application context chooses the demonstration checklist.
                  Policy approval is pending.
                </p>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const form = new FormData(e.currentTarget);
                    void perform(async () => {
                      const result = await api<{ id: string }>(
                        "/applications",
                        {
                          method: "POST",
                          body: JSON.stringify({
                            name: form.get("name"),
                            category: form.get("category"),
                            evaluation_date: form.get("evaluation_date"),
                          }),
                        },
                      );
                      await loadApplications();
                      setActive(result.id);
                      setModal(null);
                    }, "Application created.");
                  }}
                >
                  <label>
                    Institution name
                    <input name="name" required minLength={3} maxLength={120} />
                  </label>
                  <label>
                    Application context
                    <select name="category">
                      <option value="EOA">Extension of Approval</option>
                      <option value="NEW_INSTITUTION">
                        New institution · UG Engineering
                      </option>
                    </select>
                  </label>
                  <label>
                    Evaluation date
                    <input
                      type="date"
                      name="evaluation_date"
                      defaultValue="2026-10-27"
                      required
                    />
                  </label>
                  <button className="primary full" disabled={busy}>
                    Create application
                    <ArrowRight size={17} />
                  </button>
                </form>
              </>
            )}
            {modal === "source" && doc && (
              <>
                <h2 id="dialog-title">Record a source observation</h2>
                <p>
                  Record how the evidence was checked. This workspace has no
                  live issuer connector.
                </p>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const form = new FormData(e.currentTarget);
                    void perform(async () => {
                      await api("/documents/" + doc.id + "/source-checks", {
                        method: "POST",
                        body: JSON.stringify({
                          mode: form.get("mode"),
                          status: form.get("status"),
                          note: reason,
                        }),
                      });
                      setModal(null);
                      await refresh();
                    }, "Source observation recorded with its mode.");
                  }}
                >
                  <label>
                    Mode
                    <select name="mode">
                      <option value="MOCK">Mock demonstration</option>
                      <option value="MANUAL">
                        Officer-attested manual observation
                      </option>
                    </select>
                  </label>
                  <label>
                    Result
                    <select name="status">
                      <option value="SOURCE_UNAVAILABLE">
                        Source unavailable
                      </option>
                      <option value="PENDING">Pending</option>
                      <option value="VERIFIED">Verified by stated mode</option>
                      <option value="MISMATCH">Mismatch observed</option>
                    </select>
                  </label>
                  <label>
                    Source and observation
                    <textarea
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      required
                      minLength={10}
                      maxLength={1000}
                    />
                  </label>
                  <button className="primary full" disabled={busy}>
                    Save observation
                  </button>
                </form>
              </>
            )}
            {editing && (
              <>
                <h2 id="dialog-title">
                  Review {pretty(editing.key).toLowerCase()}
                </h2>
                <p>
                  Original text: <strong>{editing.raw}</strong>. Confirmation
                  appends a revision and preserves the extracted original.
                </p>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    void perform(async () => {
                      await api("/fields/" + editing.id, {
                        method: "PATCH",
                        headers: { "If-Match": String(editing.revision) },
                        body: JSON.stringify({ raw_value: editValue, reason }),
                      });
                      setEditing(null);
                      await refresh();
                    }, "Evidence fact revision saved.");
                  }}
                >
                  <label>
                    Accepted value
                    <input
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      required
                      maxLength={200}
                    />
                  </label>
                  <label>
                    Review reason
                    <textarea
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      required
                      minLength={5}
                      maxLength={500}
                    />
                  </label>
                  <button className="primary full" disabled={busy}>
                    Confirm evidence fact
                  </button>
                </form>
              </>
            )}
            {finding && (
              <>
                <h2 id="dialog-title">Review observation</h2>
                <p>{finding.title}</p>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    void perform(async () => {
                      await api("/findings/" + finding.id + "/actions", {
                        method: "POST",
                        headers: { "If-Match": String(finding.version) },
                        body: JSON.stringify({ action, reason }),
                      });
                      setFinding(null);
                      await refresh();
                    }, "Review action recorded.");
                  }}
                >
                  <label>
                    Action
                    <select
                      value={action}
                      onChange={(e) => setAction(e.target.value)}
                    >
                      {isApplicant ? (
                        <option value="RESPOND">
                          Submit applicant response
                        </option>
                      ) : (
                        <>
                          <option value="CONFIRM">Confirm observation</option>
                          <option value="DISMISS">Dismiss with reason</option>
                          <option value="VERIFY">
                            Move response to verification pending
                          </option>
                          <option value="RESOLVE">
                            Resolve confirmed observation
                          </option>
                        </>
                      )}
                    </select>
                  </label>
                  <label>
                    Reason / evidence response
                    <textarea
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      required
                      minLength={5}
                      maxLength={1000}
                    />
                  </label>
                  <button className="primary full" disabled={busy}>
                    Record review action
                  </button>
                </form>
              </>
            )}
            {error && (
              <div className="alert error" role="alert">
                {error}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
function Stat({
  label,
  value,
  sub,
  icon,
  amber = false,
}: {
  label: string;
  value: string;
  sub: string;
  icon: React.ReactNode;
  amber?: boolean;
}) {
  return (
    <section className={"stat " + (amber ? "amber-stat" : "")}>
      <div className="stat-top">
        <span>{label}</span>
        {icon}
      </div>
      <strong>{value}</strong>
      <p>{sub}</p>
    </section>
  );
}
function PanelTitle({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="panel-title">
      <div>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      {action}
    </div>
  );
}
function FindingCard({
  f,
  onEvidence,
  onReview,
  canReview,
}: {
  f: Finding;
  onEvidence: (id: string, field?: string) => void;
  onReview: () => void;
  canReview: boolean;
}) {
  return (
    <article className="panel finding-card">
      <div className="finding-top">
        <span className="finding-icon">
          <FileCheck2 size={20} />
        </span>
        <div>
          <div className="finding-label">
            {f.module.toUpperCase()} <span> / </span> {f.rule_id}
          </div>
          <h3>{f.title}</h3>
        </div>
        <Badge tone={f.state === "REVIEWER_CONFIRMED" ? "mint" : "amber"}>
          {pretty(f.state)}
        </Badge>
      </div>
      <p>{f.explanation}</p>
      <div className="finding-bottom">
        <div className="evidence-links">
          {f.evidence.slice(0, 3).map((e) => (
            <button
              key={e.field_id}
              onClick={() => onEvidence(e.document_id, e.field_id)}
            >
              <Link2 size={13} />
              Evidence · p.{e.page}
            </button>
          ))}
          {!f.evidence.length && (
            <span className="muted small">
              Missing or unconfirmed evidence explicitly identified
            </span>
          )}
        </div>
        {canReview && (
          <button className="secondary" onClick={onReview}>
            Review observation
            <ArrowRight size={15} />
          </button>
        )}
      </div>
    </article>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
