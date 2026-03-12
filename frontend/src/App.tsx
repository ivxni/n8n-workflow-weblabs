import { useState, useEffect, useCallback } from 'react'
import {
  Search, ChevronLeft, ChevronRight, Mail, Globe, Phone, MapPin,
  Star, CheckCircle, XCircle, Send, RefreshCw, Sparkles, Building2,
  TrendingUp, Users, MailCheck, ArrowRight, ExternalLink, Loader2,
  AlertCircle, Eye, Pencil, Check, X
} from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Types (unverändert)
interface Lead {
  id: number
  company_name: string
  industry: string | null
  address: string | null
  city: string | null
  postal_code: string | null
  phone: string | null
  email: string | null
  current_website: string | null
  has_website: boolean
  website_quality_score: number
  website_issues: string[] | null
  google_rating: number | null
  google_reviews_count: number | null
  generated_email_subject: string | null
  generated_email_body: string | null
  status: string
  priority: number
  source: string | null
  notes: string | null
  created_at: string
}

interface Stats {
  total_leads: number
  new_leads: number
  pending_review: number
  emails_sent: number
  responses: number
  conversion_rate: number
}

// Monochrome Status Badge
function StatusBadge({ status }: { status: string }) {
  const badges: Record<string, { class: string; label: string }> = {
    new: { class: 'bg-zinc-800 text-zinc-300 border-zinc-700', label: 'Neu' },
    reviewed: { class: 'bg-zinc-800 text-zinc-300 border-zinc-700', label: 'Geprüft' },
    approved: { class: 'bg-zinc-100 text-zinc-900 border-zinc-200', label: 'Genehmigt' },
    sent: { class: 'bg-zinc-100 text-zinc-900 border-zinc-200', label: 'Gesendet' },
    responded: { class: 'bg-zinc-100 text-zinc-900 border-zinc-200', label: 'Antwort' },
    rejected: { class: 'bg-zinc-900 text-zinc-500 border-zinc-800 line-through', label: 'Abgelehnt' },
  }
  const badge = badges[status] || badges.new
  return (
    <span className={`px-2.5 py-0.5 rounded text-xs font-medium border ${badge.class}`}>
      {badge.label}
    </span>
  )
}

// Dark Stat Card
function StatCard({ icon: Icon, label, value }: {
  icon: React.ElementType
  label: string
  value: number | string
}) {
  return (
    <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-5">
      <div className="flex items-center justify-between mb-2">
        <p className="text-zinc-500 text-sm font-medium">{label}</p>
        <Icon className="w-4 h-4 text-zinc-600" />
      </div>
      <p className="text-2xl font-bold text-zinc-100">{value}</p>
    </div>
  )
}

// Dark Lead Card
function LeadCard({ lead, isActive, onClick, onGenerateEmail, onApprove, onReject, onSendEmail, onUpdateSubject, isLoading }: {
  lead: Lead
  isActive: boolean
  onClick: () => void
  onGenerateEmail: () => void
  onApprove: (subject?: string, body?: string) => void
  onReject: () => void
  onSendEmail: () => void
  onUpdateSubject: (subject: string) => void
  isLoading: boolean
}) {
  const [showEmail, setShowEmail] = useState(false)
  const [isEditingSubject, setIsEditingSubject] = useState(false)
  const [isEditingBody, setIsEditingBody] = useState(false)
  const [editedSubject, setEditedSubject] = useState(lead.generated_email_subject || '')
  const [editedBody, setEditedBody] = useState(lead.generated_email_body || '')
  const [currentLeadId, setCurrentLeadId] = useState(lead.id)
  const [hasUserEditedBody, setHasUserEditedBody] = useState(false)
  const [hasUserEditedSubject, setHasUserEditedSubject] = useState(false)

  // Reset nur bei neuem Lead (andere ID)
  if (lead.id !== currentLeadId) {
    setCurrentLeadId(lead.id)
    setEditedSubject(lead.generated_email_subject || '')
    setEditedBody(lead.generated_email_body || '')
    setIsEditingSubject(false)
    setIsEditingBody(false)
    setHasUserEditedBody(false)
    setHasUserEditedSubject(false)
  }

  // Wenn Server neue Daten hat UND user NICHT editiert hat, dann übernehmen
  // Dies passiert z.B. wenn man "E-Mail generieren" klickt
  if (!hasUserEditedBody && lead.generated_email_body && lead.generated_email_body !== editedBody) {
    setEditedBody(lead.generated_email_body)
  }
  if (!hasUserEditedSubject && lead.generated_email_subject && lead.generated_email_subject !== editedSubject) {
    setEditedSubject(lead.generated_email_subject)
  }

  const handleBodyChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setEditedBody(e.target.value)
    setHasUserEditedBody(true)
  }

  const handleSubjectChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setEditedSubject(e.target.value)
    setHasUserEditedSubject(true)
  }

  const handleSaveSubject = (e: React.MouseEvent) => {
    e.stopPropagation()
    onUpdateSubject(editedSubject)
    setIsEditingSubject(false)
  }

  const handleApprove = (e: React.MouseEvent) => {
    e.stopPropagation()
    // Wenn wir im Edit-Mode sind, nehmen wir den bearbeiteten Text. 
    // Wenn nicht, nehmen wir auch den bearbeiteten Text (der standardmäßig dem Original entspricht), 
    // falls er sich geändert hat.
    onApprove(editedSubject, editedBody)
  }

  return (
    <div
      className={`
        bg-zinc-900 border rounded-lg overflow-hidden transition-all cursor-pointer group
        ${isActive 
          ? 'border-zinc-500 shadow-lg shadow-zinc-900/50' 
          : 'border-zinc-800 hover:border-zinc-700'
        }
      `}
      onClick={onClick}
    >
      {/* Header */}
      <div className="p-5 border-b border-zinc-800 bg-zinc-900">
        <div className="flex justify-between items-start gap-4">
          <div>
            <h3 className="font-bold text-lg text-zinc-100 leading-tight mb-1 group-hover:text-white transition-colors">
              {lead.company_name}
            </h3>
            {lead.industry && (
              <p className="text-sm text-zinc-500">{lead.industry}</p>
            )}
          </div>
          <StatusBadge status={lead.status} />
        </div>
      </div>

      {/* Content */}
      <div className="p-5 space-y-4">
        {/* Contact Info */}
        <div className="space-y-2.5 text-sm">
          {lead.address && (
            <div className="flex items-center gap-3 text-zinc-400">
              <MapPin className="w-4 h-4 text-zinc-600 flex-shrink-0" />
              <span className="truncate">{lead.address}, {lead.city}</span>
            </div>
          )}
          {lead.phone && (
            <div className="flex items-center gap-3 text-zinc-400">
              <Phone className="w-4 h-4 text-zinc-600 flex-shrink-0" />
              <span>{lead.phone}</span>
            </div>
          )}
          {lead.email ? (
            <div className="flex items-center gap-3 text-zinc-300 font-medium">
              <Mail className="w-4 h-4 text-zinc-100 flex-shrink-0" />
              <span className="truncate">{lead.email}</span>
            </div>
          ) : (
            <div className="flex items-center gap-3 text-red-400">
              <Mail className="w-4 h-4 text-red-500 flex-shrink-0" />
              <span>Keine E-Mail gefunden</span>
            </div>
          )}
          {lead.current_website ? (
            <div className="flex items-center gap-3">
              <Globe className="w-4 h-4 text-zinc-600 flex-shrink-0" />
              <a 
                href={lead.current_website} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-zinc-300 hover:text-white hover:underline truncate transition-colors"
                onClick={(e) => e.stopPropagation()}
              >
                {lead.current_website.replace(/^https?:\/\//, '')}
              </a>
            </div>
          ) : (
            <div className="flex items-center gap-3 text-zinc-500">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>Keine Website</span>
            </div>
          )}
        </div>

        {/* Email Preview */}
        {lead.generated_email_subject && (
          <div className="mt-4 pt-4 border-t border-zinc-800">
            <button
              onClick={(e) => { e.stopPropagation(); setShowEmail(!showEmail) }}
              className="flex items-center gap-2 text-sm font-medium text-zinc-400 hover:text-white transition-colors"
            >
              <Eye className="w-4 h-4" />
              {showEmail ? 'E-Mail verbergen' : 'Vorschau ansehen'}
            </button>
            
            {showEmail && (
              <div className="mt-3 bg-zinc-950 border border-zinc-800 rounded p-4 text-sm">
                
                {/* Subject Editor */}
                {isEditingSubject ? (
                  <div className="flex items-center gap-2 mb-3 border-b border-zinc-800 pb-2">
                    <input 
                      type="text" 
                      value={editedSubject}
                      onChange={handleSubjectChange}
                      onClick={(e) => e.stopPropagation()}
                      className="flex-1 bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-zinc-200 focus:outline-none focus:border-zinc-500 text-sm"
                      autoFocus
                    />
                    <button onClick={handleSaveSubject} className="p-1 hover:text-green-400 text-zinc-400"><Check className="w-4 h-4"/></button>
                    <button onClick={(e) => { e.stopPropagation(); setIsEditingSubject(false) }} className="p-1 hover:text-red-400 text-zinc-400"><X className="w-4 h-4"/></button>
                  </div>
                ) : (
                  <div className="flex items-start justify-between gap-4 mb-3 border-b border-zinc-800 pb-2 group/subject">
                    <p className="font-medium text-zinc-200">{editedSubject}</p>
                    {lead.status !== 'sent' && (
                      <button 
                        onClick={(e) => { e.stopPropagation(); setIsEditingSubject(true) }}
                        className="opacity-0 group-hover/subject:opacity-100 p-1 hover:text-white text-zinc-500 transition-opacity"
                        title="Betreff bearbeiten"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                )}
                
                {/* Body Editor */}
                <div className="relative group/body">
                  {isEditingBody ? (
                     <div onClick={(e) => e.stopPropagation()}>
                       <textarea 
                          value={editedBody}
                          onChange={handleBodyChange}
                          className="w-full h-64 bg-zinc-900 border border-zinc-700 rounded p-3 text-zinc-300 font-mono text-xs leading-relaxed focus:outline-none focus:border-zinc-500 resize-y"
                          autoFocus
                        />
                        <div className="flex justify-end gap-2 mt-2">
                          <button 
                            onClick={(e) => { e.stopPropagation(); setIsEditingBody(false) }}
                            className="text-xs text-zinc-400 hover:text-white"
                          >
                            Abbrechen (Änderungen verwerfen)
                          </button>
                          <button 
                            onClick={(e) => { e.stopPropagation(); setIsEditingBody(false) }}
                            className="text-xs text-green-400 hover:text-green-300 font-medium"
                          >
                            Fertig (zum Genehmigen bereit)
                          </button>
                        </div>
                     </div>
                  ) : (
                    <>
                      <p className="text-zinc-400 whitespace-pre-wrap font-mono text-xs leading-relaxed">
                        {editedBody}
                      </p>
                      {lead.status !== 'sent' && (
                        <button 
                          onClick={(e) => { e.stopPropagation(); setIsEditingBody(true) }}
                          className="absolute top-0 right-0 opacity-0 group-hover/body:opacity-100 p-1 hover:text-white text-zinc-500 transition-opacity bg-zinc-950/80 rounded"
                          title="Text bearbeiten"
                        >
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </>
                  )}
                </div>

              </div>
            )}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="px-5 pb-5 flex flex-wrap gap-2" onClick={(e) => e.stopPropagation()}>
        {!lead.generated_email_body && (
          <button
            onClick={onGenerateEmail}
            disabled={isLoading}
            className="flex items-center gap-2 px-3 py-1.5 bg-zinc-100 text-zinc-900 hover:bg-white
                     rounded text-sm font-medium transition-colors disabled:opacity-50"
          >
            {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
            Entwurf erstellen
          </button>
        )}
        
        {lead.generated_email_body && lead.status !== 'sent' && lead.status !== 'rejected' && (
          <>
            <button
              onClick={onGenerateEmail}
              disabled={isLoading}
              className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800 text-zinc-300 hover:bg-zinc-700 hover:text-white
                       rounded text-sm font-medium transition-colors disabled:opacity-50"
              title="E-Mail neu generieren"
            >
              {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
              Neu
            </button>
            <button
              onClick={handleApprove}
              className="flex items-center gap-2 px-3 py-1.5 bg-zinc-100 hover:bg-white text-zinc-900
                       rounded text-sm font-medium transition-colors"
            >
              <CheckCircle className="w-3.5 h-3.5" />
              Genehmigen
            </button>
            <button
              onClick={onReject}
              className="flex items-center gap-2 px-3 py-1.5 border border-zinc-700 
                       hover:bg-zinc-800 text-zinc-400 hover:text-zinc-300
                       rounded text-sm font-medium transition-colors"
            >
              <XCircle className="w-3.5 h-3.5" />
              Ablehnen
            </button>
          </>
        )}

        {lead.status === 'approved' && lead.email && (
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <span className="text-xs text-zinc-500 hidden sm:inline">
              An: <span className="text-zinc-300">{lead.email}</span>
            </span>
            <button
              onClick={onSendEmail}
              disabled={isLoading}
              className="flex items-center gap-2 px-3 py-1.5 bg-zinc-100 hover:bg-white text-zinc-900
                       disabled:opacity-50 rounded text-sm font-medium transition-colors"
            >
              {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
              Senden
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// Main App
export default function App() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [searchLoading, setSearchLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState<number | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')

  // Helper: Find next open lead
  const findNextOpenLeadIndex = useCallback((currentLeads: Lead[], startIndex: number = 0) => {
    // Suche nach dem ersten Lead, der "offen" ist (new, reviewed, approved)
    // aber NICHT sent, rejected oder responded.
    const openStatuses = ['new', 'reviewed', 'approved']
    
    // Suche ab startIndex
    for (let i = startIndex; i < currentLeads.length; i++) {
      if (openStatuses.includes(currentLeads[i].status)) return i
    }
    // Suche von vorne
    for (let i = 0; i < startIndex; i++) {
      if (openStatuses.includes(currentLeads[i].status)) return i
    }
    return startIndex
  }, [])

  // Fetch leads
  const fetchLeads = useCallback(async (preserveIndex = false) => {
    setIsLoading(true)
    try {
      const params = new URLSearchParams({ per_page: '100' })
      if (statusFilter !== 'all') params.append('status', statusFilter)
      if (searchQuery) params.append('search', searchQuery)
      
      const res = await fetch(`${API_URL}/api/leads?${params}`)
      const data = await res.json()
      const newLeads = data.leads || []
      setLeads(newLeads)

      // Auto-Focus Logic
      if (!preserveIndex && newLeads.length > 0) {
        // Beim ersten Laden: Springe zum ersten "offenen" Lead
        const nextIdx = findNextOpenLeadIndex(newLeads, 0)
        setCurrentIndex(nextIdx)
      }
    } catch (error) {
      console.error('Fehler beim Laden:', error)
    }
    setIsLoading(false)
  }, [statusFilter, searchQuery, findNextOpenLeadIndex])

  // Fetch stats
  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_URL}/api/stats`)
      const data = await res.json()
      setStats(data)
    } catch (error) {
      console.error('Stats Fehler:', error)
    }
  }

  useEffect(() => {
    fetchLeads()
    fetchStats()
  }, [fetchLeads])

  // Navigation
  const goNext = () => {
    if (leads.length > 0) {
      setCurrentIndex((prev) => (prev + 1) % leads.length)
    }
  }

  const goPrev = () => {
    if (leads.length > 0) {
      setCurrentIndex((prev) => (prev - 1 + leads.length) % leads.length)
    }
  }

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') goNext()
      if (e.key === 'ArrowLeft') goPrev()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [leads.length])

  // Search new businesses
  const searchBusinesses = async () => {
    setSearchLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          city: 'Stuttgart',
          radius_km: 60,
          max_results: 60
        })
      })
      const data = await res.json()
      alert(`✅ ${data.message}`)
      fetchLeads()
      fetchStats()
    } catch (error) {
      alert('❌ Fehler bei der Suche')
    }
    setSearchLoading(false)
  }

  // Actions with Auto-Advance
  const handleActionComplete = async () => {
    await fetchLeads(true) // Daten neu laden, Index behalten
    fetchStats()
    
    // Automatisch zum nächsten offenen Lead springen
    setLeads(prevLeads => {
      const nextIdx = findNextOpenLeadIndex(prevLeads, (currentIndex + 1) % prevLeads.length)
      setCurrentIndex(nextIdx)
      return prevLeads
    })
  }

  const generateEmail = async (leadId: number) => {
    setActionLoading(leadId)
    try {
      const res = await fetch(`${API_URL}/api/leads/${leadId}/generate-email`, { method: 'POST' })
      if (!res.ok) throw new Error('Fehler bei der Generierung')
      // Hier kein Auto-Advance, da man das Ergebnis sehen will
      fetchLeads(true)
    } catch (error) {
      alert('❌ Fehler bei der E-Mail-Generierung')
    }
    setActionLoading(null)
  }

  const approveLead = async (leadId: number, subject?: string, body?: string) => {
    try {
      const res = await fetch(`${API_URL}/api/leads/${leadId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subject, body })
      })
      if (!res.ok) throw new Error('Fehler beim Genehmigen')
      // Kein Auto-Advance, da man noch Senden muss
      fetchLeads(true)
      fetchStats()
    } catch (error) {
      alert('❌ Fehler beim Genehmigen')
    }
  }

  const rejectLead = async (leadId: number) => {
    try {
      const res = await fetch(`${API_URL}/api/leads/${leadId}/reject`, { method: 'POST' })
      if (!res.ok) throw new Error('Fehler beim Ablehnen')
      handleActionComplete() // Auto-Advance!
    } catch (error) {
      alert('❌ Fehler beim Ablehnen')
    }
  }

  const sendEmail = async (leadId: number) => {
    setActionLoading(leadId)
    try {
      const res = await fetch(`${API_URL}/api/leads/${leadId}/send-email`, { method: 'POST' })
      const data = await res.json()
      if (data.success) {
        // alert('✅ E-Mail erfolgreich gesendet!') // Nervigen Alert entfernen für Flow
      } else {
        alert(`❌ ${data.message}`)
      }
      handleActionComplete() // Auto-Advance!
    } catch (error) {
      alert('❌ Fehler beim Senden')
    }
    setActionLoading(null)
  }

  const updateLeadSubject = async (leadId: number, newSubject: string) => {
    try {
      const res = await fetch(`${API_URL}/api/leads/${leadId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ generated_email_subject: newSubject })
      })
      if (!res.ok) throw new Error('Fehler beim Aktualisieren')
      
      setLeads(prev => prev.map(l => l.id === leadId ? { ...l, generated_email_subject: newSubject } : l))
    } catch (error) {
      alert('❌ Fehler beim Speichern des Betreffs')
    }
  }

  const currentLead = leads[currentIndex]

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-300 font-sans selection:bg-zinc-700 selection:text-white">
      <div className="max-w-7xl mx-auto px-6 py-8">
        
        {/* Minimal Header */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-10">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">Lead Generator</h1>
            <p className="text-zinc-500 mt-1 text-sm">Weblabs Automation Dashboard</p>
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={searchBusinesses}
              disabled={searchLoading}
              className="flex items-center gap-2 px-4 py-2 bg-white text-zinc-900 hover:bg-zinc-200 
                       disabled:opacity-50 rounded-md text-sm font-medium transition-colors"
            >
              {searchLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              Neue Leads suchen
            </button>
            
            <button
              onClick={() => { fetchLeads(); fetchStats() }}
              className="p-2 bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 rounded-md transition-colors"
            >
              <RefreshCw className="w-4 h-4 text-zinc-400" />
            </button>
          </div>
        </header>

        {/* Stats Grid */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
            <StatCard icon={Users} label="Gesamt" value={stats.total_leads} />
            <StatCard icon={Sparkles} label="Neu" value={stats.new_leads} />
            <StatCard icon={MailCheck} label="Gesendet" value={stats.emails_sent} />
            <StatCard icon={TrendingUp} label="Conversion" value={`${stats.conversion_rate}%`} />
          </div>
        )}

        {/* Filters & Search */}
        <div className="flex flex-col md:flex-row gap-4 mb-8">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-zinc-500">Filter:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-sm text-zinc-300
                       focus:outline-none focus:ring-1 focus:ring-zinc-600"
            >
              <option value="all">Alle Status</option>
              <option value="new">Neu</option>
              <option value="reviewed">Geprüft</option>
              <option value="approved">Genehmigt</option>
              <option value="sent">Gesendet</option>
            </select>
          </div>

          <div className="flex-1">
            <input
              type="text"
              placeholder="Suchen..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-800 rounded-md px-4 py-2 text-sm text-zinc-300
                       focus:outline-none focus:ring-1 focus:ring-zinc-600 placeholder:text-zinc-600"
            />
          </div>
        </div>

        {/* Main Content */}
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-6 h-6 animate-spin text-zinc-600" />
          </div>
        ) : leads.length === 0 ? (
          <div className="text-center py-20 bg-zinc-900/30 rounded-xl border border-dashed border-zinc-800">
            <Building2 className="w-12 h-12 text-zinc-800 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-zinc-400 mb-1">Keine Leads gefunden</h3>
            <p className="text-zinc-600 text-sm">Starte eine neue Suche oder ändere die Filter.</p>
          </div>
        ) : (
          <>
            {/* Active Lead (Focus Mode) */}
            {currentLead && (
              <div className="mb-12">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold flex items-center gap-2 text-white">
                    <Star className="w-4 h-4 text-zinc-100" />
                    Aktueller Fokus
                  </h2>
                  <div className="flex items-center gap-2">
                    <button onClick={goPrev} className="p-1.5 hover:bg-zinc-800 rounded text-zinc-400 hover:text-white transition-colors">
                      <ChevronLeft className="w-5 h-5" />
                    </button>
                    <span className="text-sm font-mono text-zinc-500">
                      {currentIndex + 1}/{leads.length}
                    </span>
                    <button onClick={goNext} className="p-1.5 hover:bg-zinc-800 rounded text-zinc-400 hover:text-white transition-colors">
                      <ChevronRight className="w-5 h-5" />
                    </button>
                  </div>
                </div>
                
                <LeadCard
                  lead={currentLead}
                  isActive={true}
                  onClick={() => {}}
                  onGenerateEmail={() => generateEmail(currentLead.id)}
                  onApprove={(subject, body) => approveLead(currentLead.id, subject, body)}
                  onReject={() => rejectLead(currentLead.id)}
                  onSendEmail={() => sendEmail(currentLead.id)}
                  onUpdateSubject={(subject) => updateLeadSubject(currentLead.id, subject)}
                  isLoading={actionLoading === currentLead.id}
                />
              </div>
            )}

            {/* List View */}
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {leads.map((lead, index) => (
                <div key={lead.id} className={index === currentIndex ? 'hidden md:block opacity-50 pointer-events-none grayscale' : ''}>
                  <LeadCard
                    lead={lead}
                    isActive={false}
                    onClick={() => setCurrentIndex(index)}
                    onGenerateEmail={() => generateEmail(lead.id)}
                    onApprove={(subject, body) => approveLead(lead.id, subject, body)}
                    onReject={() => rejectLead(lead.id)}
                    onSendEmail={() => sendEmail(lead.id)}
                    onUpdateSubject={(subject) => updateLeadSubject(lead.id, subject)}
                    isLoading={actionLoading === lead.id}
                  />
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
