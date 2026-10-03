import { useEffect, useState } from 'react'
import { DEMO_LINKS } from '../api.js'

function isValidUrl(value) {
  return /^https?:\/\//i.test(value.trim())
}

function ProductURL({
  url,
  pageText,
  onUrlChange,
  onPageTextChange,
  isLoading,
  openPageText = false,
  validationError = '',
}) {
  const [showPageText, setShowPageText] = useState(openPageText)
  const validUrl = isValidUrl(url)
  const hasPageText = pageText.trim().length > 0

  useEffect(() => {
    if (openPageText) setShowPageText(true)
  }, [openPageText])

  const chooseDemo = (demoUrl) => {
    onUrlChange(demoUrl)
    onPageTextChange('')
    setShowPageText(false)
  }

  return (
    <section className="card link-card" aria-labelledby="product-link-heading">
      <div className="step-heading">
        <span className="step-number">2</span>
        <div>
          <p className="eyebrow">One last thing</p>
          <h2 id="product-link-heading">Paste the product link</h2>
        </div>
      </div>

      <label className="field">
        <span>Product page URL</span>
        <input
          type="url"
          value={url}
          onChange={(event) => onUrlChange(event.target.value)}
          placeholder="https://store.example.com/product"
          aria-invalid={Boolean(validationError) || (url.length > 0 && !validUrl)}
        />
      </label>
      {validationError && <p className="field-hint error-text" role="alert">{validationError}</p>}
      {url.length > 0 && !validUrl && (
        <p className="field-hint error-text">Use a link starting with http:// or https://.</p>
      )}
      {url.length === 0 && !pageText && (
        <p className="field-hint muted">Add a product link or choose a demo to continue.</p>
      )}

      <div className="demo-row">
        <span className="demo-label">Try a demo</span>
        {DEMO_LINKS.map((demo) => (
          <button className="demo-button" type="button" key={demo.url} onClick={() => chooseDemo(demo.url)}>
            {demo.label}
          </button>
        ))}
      </div>

      <details open={showPageText} onToggle={(event) => setShowPageText(event.currentTarget.open)}>
        <summary>Page blocked? Paste page text instead</summary>
        <label className="field page-text-field">
          <span className="visually-hidden">Page text</span>
          <textarea
            value={pageText}
            onChange={(event) => onPageTextChange(event.target.value)}
            placeholder="Paste the product description or page text here..."
            rows="6"
          />
        </label>
      </details>

      <button className="primary-button analyze-button" type="submit" disabled={isLoading}>
        {isLoading ? 'Analyzing…' : 'Analyze product'}
        {!isLoading && <span aria-hidden="true">→</span>}
      </button>
    </section>
  )
}

export default ProductURL
