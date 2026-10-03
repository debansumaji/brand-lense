const RESULT_LABELS = {
  PASS: ['pass', '✅ Pass'],
  FAIL: ['fail', '❌ Fail'],
  UNKNOWN: ['unknown', '⚪ Unknown'],
}

function ComparisonTable({ comparison = [] }) {
  if (comparison.length === 0) return null

  return (
    <section className="card comparison-card" aria-labelledby="comparison-heading">
      <div className="section-heading">
        <p className="eyebrow">Requirement check</p>
        <h2 id="comparison-heading">How it stacks up</h2>
      </div>
      <div className="comparison-scroll">
        <table className="comparison-table">
          <thead>
            <tr>
              <th scope="col">Your requirement</th>
              <th scope="col">This product</th>
              <th scope="col">Result</th>
            </tr>
          </thead>
          <tbody>
            {comparison.map((item) => {
              const [resultClass, resultLabel] = RESULT_LABELS[item.status] || RESULT_LABELS.UNKNOWN
              return (
                <tr key={item.key}>
                  <td data-label="Your requirement">
                    <span className="comparison-value">{item.requirement_text}</span>
                    {item.mandatory && <span className="deal-breaker-tag">Deal-breaker</span>}
                  </td>
                  <td data-label="This product"><span className="comparison-value">{item.product_value_text}</span></td>
                  <td data-label="Result">
                    <span className={`result-pill ${resultClass}`}>{resultLabel}</span>
                    <p className="comparison-reason">{item.reason}</p>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export default ComparisonTable
