import { useEffect, useState } from 'react'

const STEPS = [
  'Fetching product page',
  'Extracting specifications',
  'Comparing requirements',
  'Checking for missing information',
]

function Loading() {
  const [activeStep, setActiveStep] = useState(0)

  useEffect(() => {
    const timer = window.setInterval(() => {
      setActiveStep((step) => Math.min(step + 1, STEPS.length - 1))
    }, 1200)

    return () => window.clearInterval(timer)
  }, [])

  return (
    <section className="card loading-card" aria-live="polite" aria-label="Analysis progress">
      <div className="loading-orbit" aria-hidden="true" />
      <p className="eyebrow">Checking the fine print</p>
      <h1>Analyzing your product…</h1>
      <p className="muted loading-copy">We’re comparing the page against your deal-breakers.</p>
      <ol className="loading-steps">
        {STEPS.map((step, index) => {
          const complete = index < activeStep
          const current = index === activeStep
          return (
            <li className={complete ? 'is-complete' : current ? 'is-current' : ''} key={step}>
              <span className="loading-step-icon" aria-hidden="true">
                {complete ? '✓' : current ? <span className="mini-spinner" /> : index + 1}
              </span>
              <span>{step}</span>
            </li>
          )
        })}
      </ol>
    </section>
  )
}

export default Loading
