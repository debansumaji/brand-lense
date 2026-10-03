const USAGE_OPTIONS = [
  ['travel', 'Travel'],
  ['gaming', 'Gaming'],
  ['office', 'Office'],
  ['music', 'Music'],
]

function nullableNumber(value) {
  if (value === '') return null
  const number = Number(value)
  return Number.isNaN(number) ? null : number
}

function RequirementForm({ requirements, onChange }) {
  const update = (key, value) => onChange({ ...requirements, [key]: value })

  const toggleMandatory = (key) => {
    const mandatory = requirements.mandatory.includes(key)
      ? requirements.mandatory.filter((item) => item !== key)
      : [...requirements.mandatory, key]
    onChange({ ...requirements, mandatory })
  }

  const dealBreaker = (key, label) => (
    <label className="deal-breaker">
      <input
        type="checkbox"
        checked={requirements.mandatory.includes(key)}
        onChange={() => toggleMandatory(key)}
      />
      <span>{label}</span>
    </label>
  )

  return (
    <section className="card requirement-card" aria-labelledby="requirements-heading">
      <div className="step-heading">
        <span className="step-number">1</span>
        <div>
          <p className="eyebrow">Your checklist</p>
          <h2 id="requirements-heading">What do you need?</h2>
        </div>
      </div>

      <div className="field-grid">
        <label className="field field-full">
          <span>Product category</span>
          <select value={requirements.category} onChange={(event) => update('category', event.target.value)}>
            <option value="headphones">Headphones</option>
          </select>
        </label>

        <div className="field-with-deal-breaker">
          <label className="field">
            <span>Max budget</span>
            <div className="input-with-prefix">
              <span aria-hidden="true">₹</span>
              <input
                type="number"
                min="0"
                step="1"
                value={requirements.budget ?? ''}
                onChange={(event) => update('budget', nullableNumber(event.target.value))}
                placeholder="2,000"
              />
            </div>
          </label>
          {dealBreaker('budget', 'Deal-breaker')}
        </div>

        <div className="field-with-deal-breaker">
          <label className="field">
            <span>Min battery</span>
            <div className="input-with-suffix">
              <input
                type="number"
                min="0"
                step="1"
                value={requirements.battery_hours ?? ''}
                onChange={(event) => update('battery_hours', nullableNumber(event.target.value))}
                placeholder="40"
              />
              <span>hours</span>
            </div>
          </label>
          {dealBreaker('battery_hours', 'Deal-breaker')}
        </div>

        <div className="field-with-deal-breaker field-full">
          <fieldset className="field choice-field">
            <legend>ANC</legend>
            <div className="choice-row">
              {[
                ['required', 'Required'],
                ['not_required', 'Not required'],
                ['any', "Doesn't matter"],
              ].map(([value, label]) => (
                <label className="choice" key={value}>
                  <input
                    type="radio"
                    name="anc"
                    value={value}
                    checked={requirements.anc === value}
                    onChange={(event) => update('anc', event.target.value)}
                  />
                  <span>{label}</span>
                </label>
              ))}
            </div>
          </fieldset>
          {dealBreaker('anc', 'Deal-breaker')}
        </div>

        <fieldset className="field field-full choice-field">
          <legend>Usage</legend>
          <div className="choice-row">
            {USAGE_OPTIONS.map(([value, label]) => (
              <label className="choice" key={value}>
                <input
                  type="radio"
                  name="usage"
                  value={value}
                  checked={requirements.usage === value}
                  onChange={(event) => update('usage', event.target.value)}
                />
                <span>{label}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <div className="field-with-deal-breaker">
          <label className="field">
            <span>Min warranty <small>optional</small></span>
            <div className="input-with-suffix">
              <input
                type="number"
                min="0"
                step="0.5"
                value={requirements.warranty_years ?? ''}
                onChange={(event) => update('warranty_years', nullableNumber(event.target.value))}
                placeholder="1"
              />
              <span>years</span>
            </div>
          </label>
          {dealBreaker('warranty_years', 'Deal-breaker')}
        </div>
      </div>
    </section>
  )
}

export default RequirementForm
