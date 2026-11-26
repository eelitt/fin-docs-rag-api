import { useEffect, useState } from "react";

const COLUMNS = [
  ["product", "Product"],
  ["sri", "Risk indicator"],
  ["holding_period", "Recommended holding period"],
  ["ongoing_charge", "Ongoing cost"],
  ["entry_cost", "Entry cost"],
  ["exit_cost", "Exit cost"],
];

const EXAMPLES = [
  {
    label: "A passage in the longer report",
    question: "What Pharos fund size, in million euro, does the quarterly review print?",
  },
  {
    label: "A fact the corpus does not state",
    question: "What is the auditor's favorite color in the quarterly review?",
  },
  {
    label: "Should I buy this?",
    question: "Should I buy FI0008804729?",
  },
];

export function App() {
  const [sheet, setSheet] = useState(null);
  const [sheetError, setSheetError] = useState("");
  const [isinA, setIsinA] = useState("");
  const [isinB, setIsinB] = useState("");
  const [comparison, setComparison] = useState(null);
  const [compareError, setCompareError] = useState("");
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState(null);
  const [askError, setAskError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    fetch("/sheet", { signal: controller.signal })
      .then(async (response) => {
        const body = await response.json();
        if (!response.ok) {
          throw new Error(body.error || "unavailable");
        }
        return body;
      })
      .then((body) => {
        const funds = body.funds || [];
        setSheet(body);
        setIsinA(funds[0]?.isin || "");
        setIsinB(funds[1]?.isin || "");
      })
      .catch((error) => {
        if (error.name !== "AbortError") {
          setSheetError(error.message || "unavailable");
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!isinA || !isinB || isinA === isinB) {
      setComparison(null);
      setCompareError("");
      return undefined;
    }
    const controller = new AbortController();
    const params = new URLSearchParams({ isin_a: isinA, isin_b: isinB });
    fetch(`/compare?${params}`, { signal: controller.signal })
      .then(async (response) => {
        const body = await response.json();
        if (!response.ok) {
          throw new Error(body.error || "unavailable");
        }
        return body;
      })
      .then((body) => {
        setComparison(body);
        setCompareError("");
      })
      .catch((error) => {
        if (error.name !== "AbortError") {
          setComparison(null);
          setCompareError(error.message || "unavailable");
        }
      });
    return () => controller.abort();
  }, [isinA, isinB]);

  async function submitQuestion(event) {
    event.preventDefault();
    setAsking(true);
    setAskError("");
    setAnswer(null);
    try {
      const response = await fetch("/ask", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ caller: "demo", question }),
      });
      const body = await response.json();
      if (!response.ok) {
        setAskError(body.error || "unavailable");
        return;
      }
      setAnswer(body);
    } catch {
      setAskError("unavailable");
    } finally {
      setAsking(false);
    }
  }

  const funds = sheet?.funds || [];

  return (
    <main>
      <h1>fin-docs-rag</h1>
      <p className="disclaimer">
        This is a research aid over public documents. It is not investment advice, and it is not a
        product of any bank or fund company. Do not type personal holdings, amounts, or other
        personal data.
      </p>

      <h2>Fact sheet</h2>
      {sheetError ? <p>{sheetError}</p> : null}
      {!sheet && !sheetError ? <p>Loading the sheet.</p> : null}
      {sheet ? <Sheet funds={funds} /> : null}

      <h2>Comparison</h2>
      <div className="pair">
        <FundSelect label="First fund" value={isinA} funds={funds} onChange={setIsinA} />
        <FundSelect label="Second fund" value={isinB} funds={funds} onChange={setIsinB} />
      </div>
      {compareError ? <p>{compareError}</p> : null}
      {comparison ? <p>{comparison.sentence}</p> : null}
      {isinA && isinB && isinA !== isinB ? (
        <div className="pair">
          <ProductCard isin={isinA} funds={funds} />
          <ProductCard isin={isinB} funds={funds} />
        </div>
      ) : null}

      <h2>Follow-up</h2>
      <div className="examples">
        {EXAMPLES.map((example) => (
          <button
            key={example.label}
            type="button"
            className="secondary"
            onClick={() => setQuestion(example.question)}
          >
            {example.label}
          </button>
        ))}
      </div>
      <form onSubmit={submitQuestion}>
        <label htmlFor="question">Question</label>
        <textarea
          id="question"
          value={question}
          maxLength={1000}
          onChange={(event) => setQuestion(event.target.value)}
        />
        <p>
          <button type="submit" disabled={asking || !question.trim()}>
            {asking ? "Asking" : "Ask"}
          </button>
        </p>
      </form>
      {askError ? <p>{askError}</p> : null}
      {answer ? <AnswerView answer={answer} /> : null}
    </main>
  );
}

function Sheet({ funds }) {
  if (funds.length === 0) {
    return <p>The sheet has no rows.</p>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ISIN</th>
            {COLUMNS.map(([key, label]) => (
              <th key={key}>{label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {funds.map((fund) => (
            <tr key={fund.isin}>
              <th scope="row">{fund.isin}</th>
              {COLUMNS.map(([key]) => (
                <td key={key}>
                  <Cell cell={fund[key]} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Cell({ cell }) {
  if (!cell || cell.state !== "stated") {
    return cell?.state || "";
  }
  const citation = cell.citation || {};
  const where = [citation.source_id, citation.section, citation.page != null ? `p. ${citation.page}` : null]
    .filter(Boolean)
    .join(" · ");
  return (
    <>
      <span>{cell.quote}</span>
      {where ? <span className="cite">{where}</span> : null}
    </>
  );
}

function FundSelect({ label, value, funds, onChange }) {
  const id = label.replace(/\s+/g, "-").toLowerCase();
  return (
    <p>
      <label htmlFor={id}>{label}</label>
      <select id={id} value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Select a fund</option>
        {funds.map((fund) => (
          <option key={fund.isin} value={fund.isin}>
            {fund.isin}
          </option>
        ))}
      </select>
    </p>
  );
}

function ProductCard({ isin, funds }) {
  const fund = funds.find((item) => item.isin === isin);
  return (
    <article className="card">
      <h3>{isin}</h3>
      {fund ? <Cell cell={fund.product} /> : <p>Not on the sheet.</p>}
    </article>
  );
}

function AnswerView({ answer }) {
  return (
    <section>
      {answer.answer ? <p>{answer.answer}</p> : null}
      {answer.reason ? <p>{answer.reason}</p> : null}
      {answer.documents_searched?.length ? (
        <p>Documents searched: {answer.documents_searched.join(", ")}</p>
      ) : null}
      {answer.citations?.length ? (
        <ul>
          {answer.citations.map((citation, index) => (
            <li key={`${citation.source_id}-${index}`}>
              <Cell cell={{ state: "stated", quote: citation.quote, citation }} />
            </li>
          ))}
        </ul>
      ) : null}
      <Trace trace={answer.trace} />
    </section>
  );
}

function formatCost(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return value ?? "";
  }
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 8, useGrouping: false }).format(value);
}

function Trace({ trace }) {
  if (!trace) {
    return null;
  }
  const children = trace.children || [];
  return (
    <section className="trace">
      <h3>Trace</h3>
      <dl>
        <dt>Chunks</dt>
        <dd>{trace.chunk_ids?.length ? trace.chunk_ids.join(", ") : "none"}</dd>
        <dt>Tokens</dt>
        <dd>{trace.total_tokens}</dd>
        <dt>Estimated cost</dt>
        <dd>{formatCost(trace.cost_usd)} USD</dd>
        <dt>Latency</dt>
        <dd>{trace.latency_ms} ms</dd>
      </dl>
      {children.length ? (
        <ul>
          {children.map((child, index) => (
            <li key={`${child.name}-${index}`}>
              {child.name}: {child.deployment} {child.model_version}, {child.input_tokens} in,{" "}
              {child.output_tokens} out, {child.latency_ms} ms
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
