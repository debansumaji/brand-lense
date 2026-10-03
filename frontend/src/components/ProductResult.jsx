import ComparisonTable from './ComparisonTable.jsx'
import WarningBox from './WarningBox.jsx'

const VERDICTS = {
  GREAT_MATCH: {
    label: '🟢 GREAT MATCH',
    className: 'verdict-green',
    summary: (passed, total) => `${passed} of ${total} checks pass — this looks like a great match for your needs.`,
  },
  PARTIAL_MATCH: {
    label: '🟡 PARTIAL MATCH',
    className: 'verdict-amber',
    summary: (passed, total) => `${passed} of ${total} checks pass — it may work, but review the misses before buying.`,
  },
  MANDATORY_FAILED: {
    label: '🔴 DEAL-BREAKER FAILED',
    className: 'verdict-red',
    summary: (passed, total) => `${passed} of ${total} checks pass — at least one deal-breaker does not meet your needs.`,
  },
  NEEDS_VERIFICATION: {
    label: '⚪ NEEDS VERIFICATION',
    className: 'verdict-blue',
    summary: (passed, total) => `${passed} of ${total} checks pass — some key details still need verification.`,
  },
}

const SOURCE_LABELS = {
  scraped: 'Scraped from page',
  manual_text: 'From pasted text',
  demo: 'Demo page',
}

const formatter = new Intl.NumberFormat('en-IN')

function priceText(price) {
  return price == null ? 'Price not found' : `₹${formatter.format(price)}`
}

function specText(value, suffix = '') {
  return value == null ? 'Not found' : `${value}${suffix}`
}

function ReasonColumn({ title, className, items, emptyText }) {
  return (
    <div className={`reason-column ${className}`}>
      <h3>{title}</h3>
      {items.length > 0 ? (
        <ul>{items.map((item) => <li key={`${item.key}-${item.status}`}>{item.reason}</li>)}</ul>
      ) : <p className="empty-reason">{emptyText}</p>}
    </div>
  )
}

function ProductResult({ result, onAnalyzeAnother, onEditRequirements }) {
  const product = result?.product || {}
  const comparison = result?.comparison || []
  const verdict = VERDICTS[result?.verdict] || VERDICTS.NEEDS_VERIFICATION
  const passed = result?.passed ?? comparison.filter((item) => item.status === 'PASS').length
  const total = result?.total ?? comparison.length
  const score = result?.score_percent ?? (total ? Math.round((passed / total) * 100) : 0)
  const sourceLabel = SOURCE_LABELS[result?.source?.mode] || 'Analysis result'
  const passReasons = comparison.filter((item) => item.status === 'PASS')
  const failReasons = comparison.filter((item) => item.status === 'FAIL')
  const unknownReasons = comparison.filter((item) => item.status === 'UNKNOWN')
  const specs = [
    ['Battery', specText(product.battery_hours, ' hours')],
    ['ANC', product.anc == null ? 'Not found' : product.anc ? 'Yes' : 'No'],
    ['Warranty', specText(product.warranty_years, ' years')],
    ['Bluetooth', specText(product.bluetooth_version)],
  ]

  return (
    <div className="result-flow">
      <section className="card product-summary-card" aria-labelledby="result-heading">
        <div className="product-summary-topline">
          <span className="source-badge">{sourceLabel}</span>
          <span className="score-badge"><strong>{passed} / {total}</strong><span>{score}% match</span></span>
        </div>
        <p className="eyebrow">Analysis complete</p>
        <h1 id="result-heading">{product.product_name || 'Product analysis'}</h1>
        {product.brand && <p className="product-brand">{product.brand}</p>}
        <p className="product-price">{priceText(product.price)}</p>
        <div className={`verdict-banner ${verdict.className}`}>
          <strong>{verdict.label}</strong>
          <span>{verdict.summary(passed, total)}</span>
        </div>
      </section>

      <ComparisonTable comparison={comparison} />

      <section className="card reasons-card" aria-labelledby="reasons-heading">
        <div className="section-heading">
          <p className="eyebrow">The short version</p>
          <h2 id="reasons-heading">Why it matches / Why it doesn’t</h2>
        </div>
        <div className="reason-columns">
          <ReasonColumn title="Why it matches" className="reason-pass" items={passReasons} emptyText="No requirements passed yet." />
          <ReasonColumn title="Why it doesn’t" className="reason-fail" items={failReasons} emptyText="No failed requirements." />
          <ReasonColumn title="Still unknown" className="reason-unknown" items={unknownReasons} emptyText="Everything was verified." />
        </div>
      </section>

      <WarningBox warnings={result?.warnings || []} />

      <details className="card evidence-card">
        <summary>What we found on the page</summary>
        <div className="evidence-content">
          <div className="spec-chip-row">
            {specs.map(([label, value]) => <span className="spec-chip" key={label}><strong>{label}</strong>{value}</span>)}
          </div>
          <div className="evidence-snippets">
            {(product.evidence || []).length > 0 ? product.evidence.map((snippet, index) => (
              <blockquote key={`${snippet}-${index}`}>“{snippet}”</blockquote>
            )) : <p className="muted">No quoted snippets were returned.</p>}
          </div>
        </div>
      </details>

      <div className="result-actions">
        <button className="primary-button" type="button" onClick={onAnalyzeAnother}>Analyze another product</button>
        <button className="secondary-button" type="button" onClick={onEditRequirements}>Edit requirements</button>
      </div>
    </div>
  )
}

export default ProductResult
