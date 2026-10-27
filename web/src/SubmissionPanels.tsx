import React, { useEffect, useState } from "react";
import {
  Check,
  Clock3,
  Fingerprint,
  Link2,
  Plus,
  RefreshCw,
  ShieldCheck,
  X,
} from "lucide-react";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch("/v1" + path, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
    credentials: "same-origin",
  });
  const body = await response.json();
  if (!response.ok)
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : JSON.stringify(body.detail),
    );
  return body;
}

type Integration = {
  name: string;
  state: string;
  mode: string;
  detail: string;
};
export function IntegrationsPanel() {
  const [data, setData] = useState<Integration[]>([]),
    [error, setError] = useState("");
  const load = () =>
    request<{ services: Integration[] }>("/integrations")
      .then((r) => setData(r.services))
      .catch((e) => setError(e.message));
  useEffect(() => {
    void load();
  }, []);
  return (
    <>
      <section className="module-banner">
        <div className="module-icon">
          <Link2 size={25} />
        </div>
        <div>
          <span className="tiny-label">CONNECTIONS AND CAPABILITIES</span>
          <h2>Know what is actually connected.</h2>
          <p>
            Availability is separate from document accuracy and regulatory
            acceptance.
          </p>
        </div>
        <button className="secondary" onClick={() => void load()}>
          <RefreshCw size={15} />
          Check connections
        </button>
      </section>
      {error && <div className="alert error">{error}</div>}
      <div className="two-col">
        {data.map((service) => (
          <section className="panel integration-card" key={service.name}>
            <div>
              <ShieldCheck size={20} />
              <h3>{service.name}</h3>
              <span
                className={
                  "badge " +
                  (["CONNECTED", "AVAILABLE"].includes(service.state)
                    ? "mint"
                    : "amber")
                }
              >
                {service.state.replaceAll("_", " ")}
              </span>
            </div>
            <p>{service.detail}</p>
            <small>Mode: {service.mode.replaceAll("_", " ")}</small>
          </section>
        ))}
      </div>
    </>
  );
}

type Signature = {
  field: string;
  integrity?: boolean | null;
  cryptographic_validity?: boolean | null;
  trusted_chain?: boolean;
  revocation?: string;
  error?: string;
};
export type Verification = {
  id: string;
  type: string;
  mode: string;
  status: string;
  at: string;
  payload: {
    signatures?: Signature[];
    notice?: string;
    note?: string;
    decoded_references?: { text: string; status: string }[];
  };
};
type ProcessInfo = {
  layout_observations?: {kind:string;page:number;raw:string;meaning:string;suggested_value?:string[]}[];
  metrics: {
    elapsed_seconds: number;
    ocr_pages: number;
    candidate_fields: number;
    low_recognition_lines_omitted: number;
  };
  classification_candidates: { kind: string; basis: string }[];
};
type TextPage = {
  page: number;
  method: string;
  lines: { text: string; bbox: number[]; score: number | null }[];
};
const keys = [
  "BUILDING",
  "CLAIMED_FLOORS",
  "COVERED_FLOORS",
  "FDR_NUMBER",
  "HOLDER",
  "BANK",
  "PRINCIPAL_INR",
  "LIEN_INR",
  "UNRESTRICTED_CLAIM_INR",
  "VALID_UNTIL",
];
const label = (s: string) => s.replaceAll("_", " ").toLowerCase();

export function ProcessingTools({
  docId,
  processing,
  events,
  officer,
  busy,
  run,
  refresh,
}: {
  docId: string;
  processing?: ProcessInfo | null;
  events?: Verification[];
  officer: boolean;
  busy: boolean;
  run: (fn: () => Promise<void>, message?: string) => Promise<void>;
  refresh: () => Promise<void>;
}) {
  const [adding, setAdding] = useState(false),
    [pages, setPages] = useState<TextPage[]>([]),
    [selected, setSelected] = useState(""),
    [key, setKey] = useState("BUILDING"),
    [value, setValue] = useState(""),
    [reason, setReason] = useState(""),
    [error, setError] = useState("");
  useEffect(() => {
    setAdding(false);
    setSelected("");
    setPages([]);
  }, [docId]);
  const lines = pages.flatMap((p) =>
    p.lines.map((l, i) => ({
      ...l,
      page: p.page,
      method: p.method,
      id: p.page + ":" + i,
    })),
  );
  const source = lines.find((l) => l.id === selected);
  async function open() {
    setError("");
    try {
      setPages(
        (await request<{ pages: TextPage[] }>("/documents/" + docId + "/text"))
          .pages,
      );
      setAdding(true);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <>
      <div className="source-card processing-card">
        <span className="tiny-label">ACTUAL PROCESSING</span>
        {processing ? (
          <>
            <strong>
              {processing.metrics.ocr_pages
                ? "CPU OCR + native PDF"
                : "Native PDF extraction"}
            </strong>
            <small>
              {processing.metrics.elapsed_seconds.toFixed(2)} seconds ·{" "}
              {processing.metrics.ocr_pages} OCR pages ·{" "}
              {processing.metrics.candidate_fields} automatic candidates
            </small>
            {processing.metrics.low_recognition_lines_omitted > 0 && (
              <small>
                {processing.metrics.low_recognition_lines_omitted}{" "}
                low-recognition lines withheld from automatic facts
              </small>
            )}
            <small>
              Document suggestions:{" "}
              {processing.classification_candidates
                .map((c) => label(c.kind))
                .join(", ") || "No confident keyword match"}{" "}
              (heuristic)
            </small>
            {(processing.layout_observations || []).map((hint, index) => (
              <details key={index} className="verification-detail">
                <summary>Page {hint.page}: {label(hint.kind)} · review required</summary>
                <p>{hint.raw}</p>
                {hint.suggested_value && <small>Notation expands to: {hint.suggested_value.join(", ")}</small>}
                <small>{hint.meaning}</small>
              </details>
            ))}
          </>
        ) : (
          <small>Processing result is being generated.</small>
        )}
        {officer && (
          <button
            className="text-button"
            disabled={busy}
            onClick={() => void open()}
          >
            <Plus size={13} />
            Add a missing evidence fact
          </button>
        )}
      </div>
      <div className="source-card">
        <span className="tiny-label">LOCAL DOCUMENT VERIFICATION</span>
        <small>
          Cryptographic integrity is separate from issuer authenticity and
          documentary scope.
        </small>
        {officer && (
          <button
            className="text-button"
            disabled={busy}
            onClick={() =>
              void run(async () => {
                await request("/documents/" + docId + "/signature-checks", {
                  method: "POST",
                });
                await refresh();
              }, "Offline signature check recorded.")
            }
          >
            <Fingerprint size={14} />
            Check PDF signatures
          </button>
        )}
        {officer && (
          <button
            className="text-button"
            disabled={busy}
            onClick={() =>
              void run(async () => {
                await request("/documents/" + docId + "/qr-checks", {
                  method: "POST",
                });
                await refresh();
              }, "QR references decoded without visiting their URLs.")
            }
          >
            <Link2 size={14} />
            Inspect QR references
          </button>
        )}
        {(events || []).slice(0, 4).map((event) => (
          <details className="verification-detail" key={event.id}>
            <summary>
              {label(event.type)} · {label(event.status)}
            </summary>
            <small>
              Mode: {event.mode} ·{" "}
              {new Date(event.at).toLocaleString("en-IN", {
                timeZone: "Asia/Kolkata",
              })}{" "}
              IST
            </small>
            {event.payload.signatures?.map((sig) => (
              <div className="signature-fact" key={sig.field}>
                <strong>{sig.field}</strong>
                <span>
                  Byte integrity:{" "}
                  {sig.integrity === true
                    ? "intact"
                    : sig.integrity === false
                      ? "failed"
                      : "unresolved"}
                </span>
                <span>
                  Cryptographic signature:{" "}
                  {sig.cryptographic_validity === true
                    ? "valid"
                    : "not established"}
                </span>
                <span>
                  Trusted chain:{" "}
                  {sig.trusted_chain ? "established" : "not established"}
                </span>
                <span>Revocation: {sig.revocation || "unknown"}</span>
              </div>
            ))}
            {event.payload.notice && <p>{event.payload.notice}</p>}
            {event.payload.note && <p>{event.payload.note}</p>}
            {event.payload.decoded_references?.map((ref, i) => (
              <p key={i}>
                <code>{ref.text}</code>
                <br />
                {ref.status}
              </p>
            ))}
          </details>
        ))}
      </div>
      {error && (
        <div role="alert" className="alert error">
          {error}
        </div>
      )}
      {adding && (
        <div className="modal-backdrop">
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="manual-fact-title"
          >
            <button
              aria-label="Close manual fact"
              className="modal-close"
              onClick={() => setAdding(false)}
            >
              <X size={19} />
            </button>
            <h2 id="manual-fact-title">Add a source-linked fact</h2>
            <p>
              Choose the exact source line. This is a human transcription,
              preserved separately from automatic extraction.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!source) {
                  setError("Choose a source line first");
                  return;
                }
                void run(async () => {
                  await request("/documents/" + docId + "/fields", {
                    method: "POST",
                    body: JSON.stringify({
                      key,
                      raw_value: value,
                      page: source.page,
                      bbox: source.bbox,
                      reason,
                    }),
                  });
                  setAdding(false);
                  await refresh();
                }, "Manual fact added with its source region.");
              }}
            >
              <label>
                Fact type
                <select value={key} onChange={(e) => setKey(e.target.value)}>
                  {keys.map((k) => (
                    <option key={k}>{k}</option>
                  ))}
                </select>
              </label>
              <label>
                Source page and line
                <select
                  required
                  value={selected}
                  onChange={(e) => {
                    setSelected(e.target.value);
                    const l = lines.find((l) => l.id === e.target.value);
                    if (l)
                      setValue(
                        l.text.includes(":")
                          ? l.text.slice(l.text.indexOf(":") + 1).trim()
                          : l.text,
                      );
                  }}
                >
                  <option value="">Choose source evidence</option>
                  {lines.map((line) => (
                    <option value={line.id} key={line.id}>
                      Page {line.page}: {line.text.slice(0, 100)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Accepted value
                <input
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
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
                  minLength={10}
                  maxLength={500}
                />
              </label>
              <button className="primary full" disabled={busy || !source}>
                <Check size={16} />
                Save source-linked fact
              </button>
            </form>
          </section>
        </div>
      )}
    </>
  );
}
