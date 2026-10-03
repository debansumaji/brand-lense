import { useState } from 'react'
import { analyzeProduct } from './api.js'
import Loading from './components/Loading.jsx'
import ProductURL from './components/ProductURL.jsx'
import ProductResult from './components/ProductResult.jsx'
import RequirementForm from './components/RequirementForm.jsx'

const initialRequirements = {
  category: 'headphones',
  budget: 2000,
  battery_hours: 40,
  anc: 'required',
  usage: null,
  warranty_years: null,
  mandatory: ['budget', 'anc'],
}

function isHttpUrl(value) {
  return /^https?:\/\//i.test(value)
}

function App() {
  const [requirements, setRequirements] = useState(initialRequirements)
  const [url, setUrl] = useState('')
  const [pageText, setPageText] = useState('')
  const [phase, setPhase] = useState('form')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [openPageText, setOpenPageText] = useState(false)
  const [inputError, setInputError] = useState('')

  const handleSubmit = async (event) => {
    event.preventDefault()

    const trimmedUrl = url.trim()
    const trimmedPageText = pageText.trim()
    if (!trimmedUrl && !trimmedPageText) {
      setInputError('Add a product link or choose a demo to continue.')
      return
    }
    if (trimmedUrl && !trimmedPageText && !isHttpUrl(trimmedUrl)) {
      setInputError('Use a link starting with http:// or https://.')
      return
    }

    setInputError('')
    setPhase('loading')
    setError(null)

    try {
      const response = await analyzeProduct({
        url: trimmedUrl,
        page_text: trimmedPageText || null,
        requirements,
      })
      setResult(response)
      setPhase('result')
    } catch (requestError) {
      setError(requestError)
      setOpenPageText(['FETCH_FAILED', 'PAGE_BLOCKED', 'NO_PRODUCT_CONTENT'].includes(requestError.code))
      setPhase('error')
    }
  }

  const editRequirements = () => {
    setPhase('form')
    setError(null)
    setInputError('')
    setOpenPageText(false)
  }

  const tryAgain = () => {
    setPhase('form')
    setInputError('')
    setOpenPageText(['FETCH_FAILED', 'PAGE_BLOCKED', 'NO_PRODUCT_CONTENT'].includes(error?.code))
  }

  const analyzeAnother = () => {
    setUrl('')
    setPageText('')
    setResult(null)
    setError(null)
    setInputError('')
    setOpenPageText(false)
    setPhase('form')
  }

  return (
    <main className="app-shell">
      <header className="site-header">
        <div className="brand-mark" aria-hidden="true">🛒</div>
        <div>
          <p className="brand-name">BeforeYouBuy</p>
          <p className="brand-tagline">Know before you spend.</p>
        </div>
      </header>

      {phase === 'form' && (
        <form className="flow" onSubmit={handleSubmit} noValidate>
          <RequirementForm requirements={requirements} onChange={setRequirements} />
          <ProductURL
            url={url}
            pageText={pageText}
            onUrlChange={(value) => {
              setUrl(value)
              if (value.trim() || pageText.trim()) setInputError('')
            }}
            onPageTextChange={(value) => {
              setPageText(value)
              if (value.trim() || url.trim()) setInputError('')
            }}
            isLoading={false}
            openPageText={openPageText}
            validationError={inputError}
          />
        </form>
      )}

      {phase === 'loading' && <Loading />}

      {phase === 'result' && <ProductResult result={result} onAnalyzeAnother={analyzeAnother} onEditRequirements={editRequirements} />}

      {phase === 'error' && (
        <section className="card status-card error-card" role="alert">
          <div className="error-icon" aria-hidden="true">!</div>
          <p className="eyebrow">Something went wrong</p>
          <h1>{error?.message || 'We could not analyze that product.'}</h1>
          {error?.code && <p className="error-code">Error code: {error.code}</p>}
          {['FETCH_FAILED', 'PAGE_BLOCKED', 'NO_PRODUCT_CONTENT'].includes(error?.code) && (
            <p className="error-hint">Try again to paste the product details manually, or check that the product link is reachable.</p>
          )}
          <div className="status-actions">
            <button className="primary-button" type="button" onClick={tryAgain}>Try again</button>
            <button className="secondary-button" type="button" onClick={editRequirements}>Edit requirements</button>
          </div>
        </section>
      )}

      <footer className="site-footer">Specs are extracted from the seller's page and may be incomplete. Always verify before buying.</footer>
    </main>
  )
}

export default App
