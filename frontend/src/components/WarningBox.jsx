const WARNING_GROUPS = [
  { type: 'mandatory_failed', icon: '🚫', heading: 'Deal-breaker failed', className: 'warning-danger' },
  { type: 'hidden_catch', icon: '⚠️', heading: 'Hidden catch — check this', className: 'warning-caution' },
  { type: 'missing_info', icon: '⚪', heading: "Couldn't verify", className: 'warning-neutral' },
  { type: 'general', icon: 'ℹ️', heading: 'Good to know', className: 'warning-info' },
]

function WarningBox({ warnings = [] }) {
  if (warnings.length === 0) return null

  const groupedWarnings = WARNING_GROUPS.map((group) => ({
    ...group,
    items: warnings.filter((warning) => warning.type === group.type),
  })).filter((group) => group.items.length > 0)

  return (
    <section className="warnings-section" aria-labelledby="warnings-heading">
      <div className="section-heading warning-section-heading">
        <p className="eyebrow">A closer look</p>
        <h2 id="warnings-heading">Things to keep in mind</h2>
      </div>
      <div className="warning-list">
        {groupedWarnings.map((group) => (
          <div className={`warning-group ${group.className}`} key={group.type}>
            <div className="warning-heading">
              <span aria-hidden="true">{group.icon}</span>
              <h3>{group.heading}</h3>
            </div>
            <ul>
              {group.items.map((warning, index) => <li key={`${group.type}-${index}`}>{warning.message}</li>)}
            </ul>
          </div>
        ))}
      </div>
    </section>
  )
}

export default WarningBox
