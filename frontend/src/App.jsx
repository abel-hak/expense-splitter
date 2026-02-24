import { useState, useEffect, useCallback, useRef, Component } from 'react'
import './App.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api'

const CATEGORIES = [
  'food', 'transport', 'housing', 'entertainment', 'utilities',
  'shopping', 'health', 'travel', 'education', 'other',
]

/* ---- Error Boundary ---- */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <div className="empty-icon">!</div>
          <h2>Something went wrong</h2>
          <p>{this.state.error?.message || 'An unexpected error occurred.'}</p>
          <button onClick={() => window.location.reload()}>Reload</button>
        </div>
      )
    }
    return this.props.children
  }
}

/* ---- Spinner ---- */
function Spinner() {
  return <div className="spinner" aria-label="Loading" />
}

/* ---- Toast system ---- */
function Toasts({ toasts, onDismiss }) {
  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.type}`}>
          <span>{t.message}</span>
          <button className="toast-close" onClick={() => onDismiss(t.id)}>
            &times;
          </button>
        </div>
      ))}
    </div>
  )
}

/* ---- Confirm dialog ---- */
function ConfirmDialog({ message, onConfirm, onCancel }) {
  return (
    <div className="confirm-overlay" onClick={onCancel}>
      <div className="confirm-card" onClick={(e) => e.stopPropagation()}>
        <p>{message}</p>
        <div className="confirm-actions">
          <button className="secondary" onClick={onCancel}>Cancel</button>
          <button className="danger-btn" onClick={onConfirm}>Confirm</button>
        </div>
      </div>
    </div>
  )
}

/* ---- Edit Expense Modal ---- */
function EditExpenseModal({ expense, members, currentUserId, onSave, onCancel, loading }) {
  const [form, setForm] = useState({
    amount: String(expense.amount),
    description: expense.description || '',
    category: expense.category || '',
  })
  function handleSubmit(e) {
    e.preventDefault()
    const amt = parseFloat(form.amount)
    if (isNaN(amt) || amt <= 0) return
    onSave({
      amount: amt,
      description: form.description,
      category: form.category || null,
    })
  }
  return (
    <div className="confirm-overlay" onClick={onCancel}>
      <div className="confirm-card modal-wide" onClick={(e) => e.stopPropagation()}>
        <h3 style={{ margin: '0 0 0.75rem', color: '#f1f5f9', textTransform: 'none', letterSpacing: 0 }}>Edit Expense</h3>
        <form onSubmit={handleSubmit} className="form">
          <label>
            Amount
            <input type="number" step="0.01" value={form.amount}
              onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))} />
          </label>
          <label>
            Description
            <input type="text" value={form.description} maxLength={200}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
          </label>
          <label>
            Category
            <select value={form.category}
              onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}>
              <option value="">None</option>
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
              ))}
            </select>
          </label>
          <div className="confirm-actions">
            <button type="button" className="secondary" onClick={onCancel}>Cancel</button>
            <button type="submit" disabled={loading}>Save</button>
          </div>
        </form>
      </div>
    </div>
  )
}

/* ---- Chat Panel ---- */
function ChatPanel({ token, selectedGroup, onActionComplete }) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([
    { role: 'ai', text: 'Hi! I can help you manage expenses. Try saying things like:\n\n"Add $50 for dinner"\n"Who owes me?"\n"Show dashboard"' },
  ])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [messages])

  async function handleSend(e) {
    e.preventDefault()
    const text = input.trim()
    if (!text || sending) return
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', text }])
    setSending(true)
    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ message: text, group_id: selectedGroup?.id || null }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => null)
        throw new Error(err?.detail || 'Chat request failed')
      }
      const data = await res.json()
      setMessages((prev) => [...prev, { role: 'ai', text: data.reply, action: data.action }])
      if (data.action) onActionComplete(data.action)
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'ai', text: `Error: ${err.message}` }])
    } finally {
      setSending(false)
    }
  }

  return (
    <>
      <button className="chat-toggle" onClick={() => setOpen((o) => !o)} title="AI Chat Assistant">
        {open ? '\u2715' : '\u{1F4AC}'}
      </button>
      {open && (
        <div className="chat-panel">
          <div className="chat-header">
            <span className="chat-header-title">AI Assistant</span>
            {selectedGroup && <span className="chat-header-group">{selectedGroup.name}</span>}
          </div>
          <div className="chat-messages" ref={scrollRef}>
            {messages.map((msg, i) => (
              <div key={i} className={`chat-bubble chat-${msg.role}`}>
                <div className="chat-bubble-text">{msg.text}</div>
                {msg.action && <span className="chat-action-badge">{msg.action.replace('_', ' ')}</span>}
              </div>
            ))}
            {sending && (
              <div className="chat-bubble chat-ai">
                <div className="chat-typing">
                  <span /><span /><span />
                </div>
              </div>
            )}
      </div>
          <form className="chat-input-bar" onSubmit={handleSend}>
            <input
              type="text"
              placeholder="Ask anything about expenses..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={sending}
              autoFocus
            />
            <button type="submit" disabled={sending || !input.trim()}>Send</button>
          </form>
      </div>
      )}
    </>
  )
}

/* ---- Dashboard ---- */
function Dashboard({ stats, getUserName }) {
  if (!stats) return null
  const maxPaid = Math.max(...stats.member_spending.map((m) => m.paid), 1)
  return (
    <div className="dashboard">
      <div className="dash-cards">
        <div className="dash-card">
          <div className="dash-label">Total Expenses</div>
          <div className="dash-value">${stats.total_expenses.toFixed(2)}</div>
        </div>
        <div className="dash-card">
          <div className="dash-label">Expense Count</div>
          <div className="dash-value">{stats.expense_count}</div>
        </div>
        <div className="dash-card">
          <div className="dash-label">Your Balance</div>
          <div className={`dash-value ${stats.your_balance >= 0 ? 'positive' : 'negative'}`}>
            {stats.your_balance >= 0 ? `+$${stats.your_balance.toFixed(2)}` : `-$${(-stats.your_balance).toFixed(2)}`}
          </div>
        </div>
      </div>
      {Object.keys(stats.category_totals).length > 0 && (
        <div className="dash-section">
          <h4>By Category</h4>
          <div className="dash-bars">
            {Object.entries(stats.category_totals).sort((a, b) => b[1] - a[1]).map(([cat, amt]) => (
              <div key={cat} className="dash-bar-row">
                <span className="dash-bar-label">{cat}</span>
                <div className="dash-bar-track">
                  <div className="dash-bar-fill" style={{ width: `${(amt / stats.total_expenses) * 100}%` }} />
                </div>
                <span className="dash-bar-value">${amt.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {stats.member_spending.length > 0 && (
        <div className="dash-section">
          <h4>Paid By Member</h4>
          <div className="dash-bars">
            {stats.member_spending.sort((a, b) => b.paid - a.paid).map((m) => (
              <div key={m.user_id} className="dash-bar-row">
                <span className="dash-bar-label">{m.name}</span>
                <div className="dash-bar-track">
                  <div className="dash-bar-fill" style={{ width: `${(m.paid / maxPaid) * 100}%` }} />
                </div>
                <span className="dash-bar-value">${m.paid.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function App() {
  const [token, setToken] = useState(null)
  const [currentUser, setCurrentUser] = useState(null)
  const [authMode, setAuthMode] = useState('login')
  const [authForm, setAuthForm] = useState({ email: '', name: '', password: '' })
  const [groups, setGroups] = useState([])
  const [groupsLoaded, setGroupsLoaded] = useState(false)
  const [selectedGroup, setSelectedGroup] = useState(null)
  const [expenses, setExpenses] = useState([])
  const [settlements, setSettlements] = useState(null)
  const [dashboard, setDashboard] = useState(null)
  const [newGroupName, setNewGroupName] = useState('')
  const [newGroupDesc, setNewGroupDesc] = useState('')
  const [newExpense, setNewExpense] = useState({ amount: '', description: '', category: '' })
  const [splitMode, setSplitMode] = useState('all')
  const [customShares, setCustomShares] = useState({})
  const [newMemberEmail, setNewMemberEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [toasts, setToasts] = useState([])
  const [confirmDialog, setConfirmDialog] = useState(null)
  const [editingExpense, setEditingExpense] = useState(null)
  const [editingGroup, setEditingGroup] = useState(false)
  const [editGroupForm, setEditGroupForm] = useState({ name: '', description: '' })
  const [searchQuery, setSearchQuery] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  const [theme, setTheme] = useState(() => localStorage.getItem('es_theme') || 'dark')
  const [activeTab, setActiveTab] = useState('expenses')
  const toastIdRef = useRef(0)
  const [mobileTab, setMobileTab] = useState('groups')

  const isAuthed = !!token

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('es_theme', theme)
  }, [theme])

  function addToast(message, type = 'error') {
    const id = ++toastIdRef.current
    setToasts((prev) => [...prev, { id, message, type }])
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000)
  }
  function dismissToast(id) {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }
  function confirmAction(message) {
    return new Promise((resolve) => {
      setConfirmDialog({
        message,
        onConfirm: () => { setConfirmDialog(null); resolve(true) },
        onCancel: () => { setConfirmDialog(null); resolve(false) },
      })
    })
  }

  async function apiRequest(path, method = 'GET', body, tk) {
    const t = tk || token
    const res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(t ? { Authorization: `Bearer ${t}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    })
    if (res.status === 401) {
      handleLogout()
      throw new Error('Session expired. Please log in again.')
    }
    if (!res.ok) {
      const text = await res.text()
      try {
        const data = text ? JSON.parse(text) : null
        if (data?.detail) {
          throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))
        }
      } catch (e) {
        if (e instanceof Error && e.message !== text) throw e
      }
      throw new Error(text || `Request failed (${res.status})`)
    }
    if (res.status === 204) return null
    return res.json()
  }

  function getUserName(userId) {
    if (userId === currentUser?.id) return 'You'
    const member = selectedGroup?.members?.find((m) => m.id === userId)
    if (member) return member.name || member.email
    return `User ${userId}`
  }
  function getSettlementUserName(userId) {
    if (userId === currentUser?.id) return 'You'
    const member = settlements?.members?.find((m) => m.id === userId)
    if (member) return member.name || member.email
    return `User ${userId}`
  }

  useEffect(() => {
    const stored = localStorage.getItem('expense_splitter_auth')
    if (!stored) return
    try {
      const parsed = JSON.parse(stored)
      if (parsed?.access_token && parsed?.user) {
        setToken(parsed.access_token)
        setCurrentUser(parsed.user)
      }
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    if (token && currentUser) {
      localStorage.setItem('expense_splitter_auth', JSON.stringify({ access_token: token, user: currentUser }))
    } else {
      localStorage.removeItem('expense_splitter_auth')
    }
  }, [token, currentUser])

  const loadGroups = useCallback(async (tk) => {
    const t = tk || token
    if (!t) return
    setLoading(true)
    try {
      const data = await apiRequest('/groups', 'GET', undefined, t)
      setGroups(data)
      setGroupsLoaded(true)
    } catch (err) { addToast(err.message) }
    finally { setLoading(false) }
  }, [token]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { if (token) loadGroups(token) }, [token]) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleAuthSubmit(e) {
    e.preventDefault()
    setLoading(true)
    try {
      const path = authMode === 'login' ? '/auth/login' : '/auth/register'
      const payload = authMode === 'login' ? { email: authForm.email, password: authForm.password } : authForm
      const data = await apiRequest(path, 'POST', payload)
      setToken(data.access_token)
      setCurrentUser(data.user)
      addToast(`Welcome, ${data.user.name || data.user.email}!`, 'success')
    } catch (err) { addToast(err.message) }
    finally { setLoading(false) }
  }

  function handleLogout() {
    setToken(null); setCurrentUser(null); setGroups([]); setGroupsLoaded(false)
    setSelectedGroup(null); setExpenses([]); setSettlements(null); setDashboard(null)
  }

  async function handleCreateGroup(e) {
    e.preventDefault()
    if (!newGroupName.trim()) return
    setLoading(true)
    try {
      const g = await apiRequest('/groups', 'POST', { name: newGroupName, description: newGroupDesc, member_ids: [] }, token)
      setGroups((prev) => [...prev, g])
      setNewGroupName(''); setNewGroupDesc('')
      addToast(`Group "${g.name}" created`, 'success')
    } catch (err) { addToast(err.message) }
    finally { setLoading(false) }
  }

  async function handleDeleteGroup() {
    if (!selectedGroup) return
    const ok = await confirmAction(`Delete group "${selectedGroup.name}" and all its expenses?`)
    if (!ok) return
    setLoading(true)
    try {
      await apiRequest(`/groups/${selectedGroup.id}`, 'DELETE', undefined, token)
      setGroups((prev) => prev.filter((g) => g.id !== selectedGroup.id))
      setSelectedGroup(null); setExpenses([]); setSettlements(null); setDashboard(null)
      addToast('Group deleted', 'success')
    } catch (err) { addToast(err.message) }
    finally { setLoading(false) }
  }

  async function handleUpdateGroup(e) {
    e.preventDefault()
    if (!selectedGroup) return
    setLoading(true)
    try {
      const updated = await apiRequest(`/groups/${selectedGroup.id}`, 'PATCH', editGroupForm, token)
      setSelectedGroup(updated)
      setGroups((prev) => prev.map((g) => g.id === updated.id ? updated : g))
      setEditingGroup(false)
      addToast('Group updated', 'success')
    } catch (err) { addToast(err.message) }
    finally { setLoading(false) }
  }

  async function handleAddMember(e) {
    e.preventDefault()
    if (!selectedGroup || !newMemberEmail.trim()) return
    setLoading(true)
    try {
      const updated = await apiRequest(`/groups/${selectedGroup.id}/members`, 'POST', { email: newMemberEmail }, token)
      setSelectedGroup(updated)
      setNewMemberEmail('')
      addToast('Member added', 'success')
    } catch (err) { addToast(err.message) }
    finally { setLoading(false) }
  }

  async function handleRemoveMember(userId) {
    if (!selectedGroup) return
    const member = selectedGroup.members.find((m) => m.id === userId)
    const name = member?.name || member?.email || `User ${userId}`
    const ok = await confirmAction(`Remove ${name} from this group?`)
    if (!ok) return
    setLoading(true)
    try {
      const updated = await apiRequest(`/groups/${selectedGroup.id}/members/${userId}`, 'DELETE', undefined, token)
      setSelectedGroup(updated)
      addToast(`${name} removed`, 'success')
    } catch (err) { addToast(err.message) }
    finally { setLoading(false) }
  }

  async function selectGroup(group) {
    setSelectedGroup(group); setSettlements(null); setDashboard(null)
    setSplitMode('all'); setCustomShares({}); setMobileTab('expenses')
    setSearchQuery(''); setFilterCategory(''); setActiveTab('expenses')
    setLoading(true)
    try {
      const freshGroup = await apiRequest(`/groups/${group.id}`, 'GET', undefined, token)
      setSelectedGroup(freshGroup)
      const exps = await apiRequest(`/expenses?group_id=${group.id}`, 'GET', undefined, token)
      setExpenses(exps)
    } catch (err) { addToast(err.message) }
    finally { setLoading(false) }
  }

  async function loadFilteredExpenses() {
    if (!selectedGroup) return
    setLoading(true)
    try {
      let url = `/expenses?group_id=${selectedGroup.id}`
      if (searchQuery) url += `&search=${encodeURIComponent(searchQuery)}`
      if (filterCategory) url += `&category=${encodeURIComponent(filterCategory)}`
      const exps = await apiRequest(url, 'GET', undefined, token)
      setExpenses(exps)
    } catch (err) { addToast(err.message) }
    finally { setLoading(false) }
  }

  useEffect(() => {
    if (!selectedGroup) return
    const timer = setTimeout(() => loadFilteredExpenses(), 300)
    return () => clearTimeout(timer)
  }, [searchQuery, filterCategory]) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleAddExpense(e) {
    e.preventDefault()
    if (!selectedGroup || !currentUser) return
    const amountNum = parseFloat(newExpense.amount)
    if (isNaN(amountNum) || amountNum <= 0) { addToast('Enter a valid amount'); return }
    if (amountNum > 999999) { addToast('Amount too large'); return }
    setLoading(true)
    try {
      let participantIds, splitType = 'equal', shares

      if (splitMode === 'custom') {
        splitType = 'custom'; shares = {}
        for (const [uid, val] of Object.entries(customShares)) {
          const v = parseFloat(val)
          if (isNaN(v) || v < 0) { addToast('All custom shares must be valid numbers'); setLoading(false); return }
          if (v > 0) shares[Number(uid)] = v
        }
        participantIds = Object.keys(shares).map(Number)
        if (participantIds.length === 0) { addToast('At least one participant must have a share > 0'); setLoading(false); return }
        const total = Object.values(shares).reduce((a, b) => a + b, 0)
        if (Math.abs(total - amountNum) > 0.01) {
          addToast(`Shares total $${total.toFixed(2)} but expense is $${amountNum.toFixed(2)}`); setLoading(false); return
        }
      } else if (splitMode === 'all') {
        participantIds = selectedGroup.member_ids
      } else {
        participantIds = [currentUser.id]
      }

      const body = {
        group_id: selectedGroup.id, payer_id: currentUser.id,
        amount: amountNum, description: newExpense.description,
        participant_ids: participantIds, split_type: splitType,
        category: newExpense.category || null,
        ...(shares ? { shares } : {}),
      }
      const exp = await apiRequest('/expenses', 'POST', body, token)
      setExpenses((prev) => [exp, ...prev])
      setNewExpense({ amount: '', description: '', category: '' }); setCustomShares({})
      addToast('Expense added', 'success')
    } catch (err) { addToast(err.message) }
    finally { setLoading(false) }
  }

  async function handleEditExpense(updates) {
    if (!editingExpense) return
    setLoading(true)
    try {
      const updated = await apiRequest(`/expenses/${editingExpense.id}`, 'PATCH', updates, token)
      setExpenses((prev) => prev.map((e) => e.id === updated.id ? updated : e))
      setEditingExpense(null)
      addToast('Expense updated', 'success')
    } catch (err) { addToast(err.message) }
    finally { setLoading(false) }
  }

  async function handleDeleteExpense(expenseId) {
    const ok = await confirmAction('Delete this expense?')
    if (!ok) return
    setLoading(true)
    try {
      await apiRequest(`/expenses/${expenseId}`, 'DELETE', undefined, token)
      setExpenses((prev) => prev.filter((e) => e.id !== expenseId))
      addToast('Expense deleted', 'success')
    } catch (err) { addToast(err.message) }
    finally { setLoading(false) }
  }

  async function loadSettlements() {
    if (!selectedGroup) return
    setLoading(true)
    try {
      const data = await apiRequest(`/settlements/group/${selectedGroup.id}`, 'GET', undefined, token)
      setSettlements(data)
      setActiveTab('settlements')
    } catch (err) { addToast(err.message) }
    finally { setLoading(false) }
  }

  async function loadDashboard() {
    if (!selectedGroup) return
    setLoading(true)
    try {
      const data = await apiRequest(`/settlements/dashboard/${selectedGroup.id}`, 'GET', undefined, token)
      setDashboard(data)
      setActiveTab('dashboard')
    } catch (err) { addToast(err.message) }
    finally { setLoading(false) }
  }

  async function handleSettleUp(toUserId, amount) {
    if (!selectedGroup) return
    setLoading(true)
    try {
      await apiRequest('/settlements/pay', 'POST', {
        group_id: selectedGroup.id, to_user_id: toUserId, amount,
      }, token)
      addToast('Payment recorded', 'success')
      loadSettlements()
    } catch (err) { addToast(err.message) }
    finally { setLoading(false) }
  }

  async function handleExport() {
    if (!selectedGroup) return
    try {
      const t = token
      const res = await fetch(`${API_BASE}/expenses/export?group_id=${selectedGroup.id}`, {
        headers: { Authorization: `Bearer ${t}` },
      })
      if (!res.ok) throw new Error('Export failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `expenses-${selectedGroup.name}.csv`
      a.click()
      URL.revokeObjectURL(url)
      addToast('CSV exported', 'success')
    } catch (err) { addToast(err.message) }
  }

  async function handleChatAction(action) {
    if (!selectedGroup) {
      await loadGroups(token)
      return
    }
    if (action === 'add_expense' || action === 'list_expenses') {
      const exps = await apiRequest(`/expenses?group_id=${selectedGroup.id}`, 'GET', undefined, token).catch(() => null)
      if (exps) setExpenses(exps)
    }
    if (action === 'settle_debt') {
      loadSettlements()
    }
    if (action === 'add_member') {
      const freshGroup = await apiRequest(`/groups/${selectedGroup.id}`, 'GET', undefined, token).catch(() => null)
      if (freshGroup) setSelectedGroup(freshGroup)
    }
    await loadGroups(token)
  }

  useEffect(() => {
    if (splitMode === 'custom' && selectedGroup?.members) {
      const init = {}
      selectedGroup.members.forEach((m) => { init[m.id] = '' })
      setCustomShares(init)
    }
  }, [splitMode, selectedGroup])

  return (
    <div className="app-root">
      <Toasts toasts={toasts} onDismiss={dismissToast} />
      {confirmDialog && <ConfirmDialog {...confirmDialog} />}
      {editingExpense && (
        <EditExpenseModal
          expense={editingExpense}
          members={selectedGroup?.members || []}
          currentUserId={currentUser?.id}
          onSave={handleEditExpense}
          onCancel={() => setEditingExpense(null)}
          loading={loading}
        />
      )}

      <header className="app-header">
        <h1>Expense Splitter</h1>
        <div className="header-actions">
          <button
            className="icon-btn"
            title={theme === 'dark' ? 'Switch to light' : 'Switch to dark'}
            onClick={() => setTheme((t) => t === 'dark' ? 'light' : 'dark')}
          >
            {theme === 'dark' ? '\u2600' : '\u263E'}
          </button>
          {isAuthed && currentUser && (
            <div className="user-info">
              <span>{currentUser.name || currentUser.email}</span>
              <button className="secondary" onClick={handleLogout}>Log out</button>
            </div>
          )}
        </div>
      </header>

      {loading && <Spinner />}

      {!isAuthed ? (
        <main className="layout-center">
          <div className="auth-card">
            <div className="auth-toggle">
              <button className={authMode === 'login' ? 'active' : ''} onClick={() => setAuthMode('login')}>Sign in</button>
              <button className={authMode === 'register' ? 'active' : ''} onClick={() => setAuthMode('register')}>Sign up</button>
            </div>
            <form onSubmit={handleAuthSubmit} className="form">
              <label>
                Email
                <input type="email" required placeholder="you@example.com" maxLength={100}
                  value={authForm.email} onChange={(e) => setAuthForm((f) => ({ ...f, email: e.target.value }))} />
              </label>
              {authMode === 'register' && (
                <label>
                  Name
                  <input type="text" placeholder="Your name" maxLength={50}
                    value={authForm.name} onChange={(e) => setAuthForm((f) => ({ ...f, name: e.target.value }))} />
                </label>
              )}
              <label>
                Password
                <input type="password" required placeholder="Enter password" minLength={4} maxLength={128}
                  value={authForm.password} onChange={(e) => setAuthForm((f) => ({ ...f, password: e.target.value }))} />
              </label>
              <button type="submit" disabled={loading} style={{ marginTop: '0.3rem' }}>
                {loading ? 'Please wait...' : authMode === 'login' ? 'Sign in' : 'Create account'}
              </button>
            </form>
          </div>
        </main>
      ) : (
        <>
          <ChatPanel token={token} selectedGroup={selectedGroup} onActionComplete={handleChatAction} />
          <div className="mobile-tabs">
            <button className={mobileTab === 'groups' ? 'active' : ''} onClick={() => setMobileTab('groups')}>Groups</button>
            <button className={mobileTab === 'expenses' ? 'active' : ''} onClick={() => setMobileTab('expenses')}>Expenses</button>
          </div>

          <main className="layout-two-column">
            {/* -------- LEFT: Groups -------- */}
            <section className={`panel panel-groups ${mobileTab === 'groups' ? 'mobile-show' : 'mobile-hide'}`}>
              <div className="panel-header">
                <h2>Groups</h2>
                <button className="secondary" onClick={() => loadGroups()} disabled={loading}>Refresh</button>
              </div>

              <form onSubmit={handleCreateGroup} className="form compact">
                <input type="text" placeholder="Group name" maxLength={60} value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)} />
                <input type="text" placeholder="Description (optional)" maxLength={200} value={newGroupDesc}
                  onChange={(e) => setNewGroupDesc(e.target.value)} />
                <button type="submit" disabled={loading}>Create</button>
              </form>

              {selectedGroup && (
                <div className="group-meta">
                  <div className="group-meta-header">
                    {editingGroup ? (
                      <form onSubmit={handleUpdateGroup} className="group-edit-form">
                        <input type="text" value={editGroupForm.name} maxLength={60}
                          onChange={(e) => setEditGroupForm((f) => ({ ...f, name: e.target.value }))} placeholder="Group name" />
                        <input type="text" value={editGroupForm.description} maxLength={200}
                          onChange={(e) => setEditGroupForm((f) => ({ ...f, description: e.target.value }))} placeholder="Description" />
                        <div className="group-edit-actions">
                          <button type="submit" disabled={loading}>Save</button>
                          <button type="button" className="secondary" onClick={() => setEditingGroup(false)}>Cancel</button>
                        </div>
                      </form>
                    ) : (
                      <>
                        <div className="group-meta-title">Members</div>
                        <div className="group-meta-actions">
                          <button className="icon-btn" title="Edit group"
                            onClick={() => {
                              setEditGroupForm({ name: selectedGroup.name, description: selectedGroup.description || '' })
                              setEditingGroup(true)
                            }}>&#9998;</button>
                          <button className="delete-btn" title="Delete group" onClick={handleDeleteGroup}>&times;</button>
                        </div>
                      </>
                    )}
                  </div>
                  {!editingGroup && (
                    <>
                      <div className="group-meta-members">
                        {selectedGroup.members?.map((m) => (
                          <span key={m.id} className={m.id === currentUser?.id ? 'member-pill you' : 'member-pill'}>
                            {m.id === currentUser?.id ? 'You' : m.name || m.email}
                            {m.id !== currentUser?.id && (
                              <button className="pill-remove" title="Remove member"
                                onClick={() => handleRemoveMember(m.id)}>&times;</button>
                            )}
                          </span>
                        ))}
                      </div>
                      <form onSubmit={handleAddMember} className="group-add-member">
                        <input type="email" placeholder="Add member by email" value={newMemberEmail}
                          onChange={(e) => setNewMemberEmail(e.target.value)} />
                        <button type="submit" disabled={loading}>Add</button>
                      </form>
                    </>
                  )}
                </div>
              )}

              <ul className="list">
                {groups.map((g) => (
                  <li key={g.id} className={selectedGroup?.id === g.id ? 'list-item active' : 'list-item'}
                    onClick={() => selectGroup(g)}>
                    <div className="list-title">{g.name}</div>
                    {g.description && <div className="list-subtitle">{g.description}</div>}
                    <div className="list-subtitle">
                      {g.members
                        ? g.members.map((m) => m.id === currentUser?.id ? 'You' : m.name || m.email).join(', ')
                        : `${g.member_ids?.length || 0} members`}
                    </div>
                  </li>
                ))}
                {groupsLoaded && groups.length === 0 && (
                  <li className="list-empty">No groups yet &mdash; create one above.</li>
                )}
              </ul>
            </section>

            {/* -------- RIGHT: Expenses + Settlements + Dashboard -------- */}
            <section className={`panel panel-expenses ${mobileTab === 'expenses' ? 'mobile-show' : 'mobile-hide'}`}>
              {selectedGroup ? (
                <>
                  <div className="panel-header">
                    <h2>{selectedGroup.name}</h2>
                    <div className="panel-header-actions">
                      <button className="secondary" onClick={handleExport} disabled={loading}>Export</button>
                    </div>
                  </div>

                  {/* Sub-tabs */}
                  <div className="sub-tabs">
                    <button className={activeTab === 'expenses' ? 'active' : ''} onClick={() => setActiveTab('expenses')}>Expenses</button>
                    <button className={activeTab === 'settlements' ? 'active' : ''} onClick={loadSettlements} disabled={loading}>Settle Up</button>
                    <button className={activeTab === 'dashboard' ? 'active' : ''} onClick={loadDashboard} disabled={loading}>Dashboard</button>
                  </div>

                  {activeTab === 'expenses' && (
                    <>
                      {/* Search & Filter */}
                      <div className="search-bar">
                        <input type="text" placeholder="Search expenses..." value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)} />
                        <select value={filterCategory} onChange={(e) => setFilterCategory(e.target.value)}>
                          <option value="">All categories</option>
                          {CATEGORIES.map((c) => (
                            <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
                          ))}
                        </select>
                      </div>

                      {/* Split toggle */}
                      <div className="split-toggle">
                        <span>Split:</span>
                        <div className="split-toggle-buttons">
                          <button type="button" className={splitMode === 'all' ? 'active' : ''} onClick={() => setSplitMode('all')}>All</button>
                          <button type="button" className={splitMode === 'me' ? 'active' : ''} onClick={() => setSplitMode('me')}>Me</button>
                          <button type="button" className={splitMode === 'custom' ? 'active' : ''} onClick={() => setSplitMode('custom')}>Custom</button>
                        </div>
                      </div>

                      {splitMode === 'custom' && selectedGroup.members && (
                        <div className="custom-shares">
                          {selectedGroup.members.map((m) => (
                            <div key={m.id} className="custom-share-row">
                              <span className="custom-share-name">{m.id === currentUser?.id ? 'You' : m.name || m.email}</span>
                              <input type="number" step="0.01" min="0" placeholder="0.00"
                                value={customShares[m.id] ?? ''}
                                onChange={(e) => setCustomShares((prev) => ({ ...prev, [m.id]: e.target.value }))} />
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Add expense form */}
                      <form onSubmit={handleAddExpense} className="form compact">
                        <input type="number" step="0.01" placeholder="Amount" max="999999"
                          value={newExpense.amount} onChange={(e) => setNewExpense((v) => ({ ...v, amount: e.target.value }))} />
                        <input type="text" placeholder="Description" maxLength={200}
                          value={newExpense.description} onChange={(e) => setNewExpense((v) => ({ ...v, description: e.target.value }))} />
                        <select value={newExpense.category} onChange={(e) => setNewExpense((v) => ({ ...v, category: e.target.value }))}>
                          <option value="">Category</option>
                          {CATEGORIES.map((c) => (
                            <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
                          ))}
                        </select>
                        <button type="submit" disabled={loading}>Add</button>
                      </form>

                      <h3>Expenses ({expenses.length})</h3>
                      <ul className="list">
                        {expenses.map((exp) => (
                          <li key={exp.id} className="list-item expense-item">
                            <div className="expense-content" onClick={() => setEditingExpense(exp)} title="Click to edit">
                              <div className="list-title">
                                ${exp.amount.toFixed(2)} &ndash; {exp.description || 'No description'}
                                {exp.category && <span className="category-tag">{exp.category}</span>}
                              </div>
                              <div className="list-subtitle">
                                Paid by {getUserName(exp.payer_id)}
                                {exp.split_type === 'custom' && exp.shares
                                  ? ` · Custom: ${Object.entries(exp.shares).map(([uid, amt]) => `${getUserName(Number(uid))} $${amt.toFixed(2)}`).join(', ')}`
                                  : ` · Split: ${exp.participant_ids.map((id) => getUserName(id)).join(', ')}`}
                              </div>
                            </div>
                            <button className="delete-btn" title="Delete expense"
                              onClick={(e) => { e.stopPropagation(); handleDeleteExpense(exp.id) }}>&times;</button>
                          </li>
                        ))}
                        {expenses.length === 0 && (
                          <li className="list-empty">
                            {searchQuery || filterCategory ? 'No matching expenses found.' : 'No expenses yet for this group.'}
                          </li>
                        )}
                      </ul>
                    </>
                  )}

                  {activeTab === 'settlements' && settlements && (
                    <>
                      <h3>Balances</h3>
                      <div className="settlements">
                        <div className="balances">
                          <ul>
                            {settlements.balances.map((b) => (
                              <li key={b.user_id} className={b.balance >= 0 ? 'positive' : 'negative'}>
                                <strong>{getSettlementUserName(b.user_id)}</strong>{' '}
                                {b.balance >= 0 ? `is owed $${b.balance.toFixed(2)}` : `owes $${(-b.balance).toFixed(2)}`}
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>

                      <h3>Suggested Transfers</h3>
                      {settlements.settlements.length === 0 ? (
                        <div className="list-empty" style={{ marginTop: '0.5rem' }}>Everyone is settled up!</div>
                      ) : (
                        <ul className="settle-list">
                          {settlements.settlements.map((s, idx) => (
                            <li key={idx} className="settle-item">
                              <div className="settle-info">
                                <strong>{getSettlementUserName(s.from_user_id)}</strong> pays{' '}
                                <strong>{getSettlementUserName(s.to_user_id)}</strong>{' '}
                                <span className="settle-amount">${s.amount.toFixed(2)}</span>
                              </div>
                              {s.from_user_id === currentUser?.id && (
                                <button className="settle-btn"
                                  onClick={() => handleSettleUp(s.to_user_id, s.amount)}
                                  disabled={loading}>
                                  Settle
                                </button>
                              )}
                            </li>
                          ))}
                        </ul>
                      )}
                    </>
                  )}

                  {activeTab === 'dashboard' && (
                    <Dashboard stats={dashboard} getUserName={getUserName} />
                  )}
                </>
              ) : (
                <div className="empty-state">
                  <div className="empty-icon">$</div>
                  <h2>Select a group</h2>
                  <p>Choose a group from the list or create a new one to start tracking expenses.</p>
                </div>
              )}
            </section>
          </main>
        </>
      )}
    </div>
  )
}

export default function Root() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  )
}
