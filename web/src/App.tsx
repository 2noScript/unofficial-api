import React, { useState, useEffect } from "react";
import { 
  Shield, 
  Key, 
  Plus, 
  Trash2, 
  RefreshCw, 
  Activity, 
  ExternalLink,
  Edit2,
  Zap,
  Globe,
  Database,
  AlertTriangle,
  Play,
  CheckCircle2,
  XCircle,
  Loader2,
  Sparkles,
  Clock,
  Copy,
  Check,
  Code,
  MessageSquare
} from "lucide-react";


import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";

interface Profile {
  id: string;
  type: "deepseek" | "gemini";
  name: string;
  token?: string | null;
  cookie?: string | null;
  is_active: boolean;
  total_requests?: number;
  request_counts?: Record<string, Record<string, number>>;
  created_at: string;
  updated_at: string;
}

interface TestResult {
  status: "ok" | "error";
  profile_id: string;
  type: string;
  model: string;
  latency_ms: number;
  reply?: string | null;
  error?: string | null;
  rawJson?: any;
}


interface ApiKey {
  id: string;
  name: string;
  key?: string;
  prefix?: string;
  created_at: string;
}

interface HealthInfo {
  status: string;
  deepseek_active_profiles: number;
  gemini_active_profiles: number;
}


export function App() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [activeTab, setActiveTab] = useState<"profiles" | "keys">("profiles");
  const [loading, setLoading] = useState(false);

  // New Profile Form State
  const [showAddProfileModal, setShowAddProfileModal] = useState(false);
  const [newProfileType, setNewProfileType] = useState<"deepseek" | "gemini">("deepseek");
  const [newProfileName, setNewProfileName] = useState("");
  const [newProfileCredential, setNewProfileCredential] = useState("");
  const [newProfileIsActive, setNewProfileIsActive] = useState(true);

  // Edit Profile Modal State
  const [editingProfile, setEditingProfile] = useState<Profile | null>(null);
  const [editName, setEditName] = useState("");
  const [editCredential, setEditCredential] = useState("");
  const [editIsActive, setEditIsActive] = useState(true);

  // Confirm Delete Profile Modal State
  const [deletingProfile, setDeletingProfile] = useState<Profile | null>(null);

  // View Profile Stats Modal State
  const [viewStatsProfile, setViewStatsProfile] = useState<Profile | null>(null);

  // New Key Modal State
  const [showAddKeyModal, setShowAddKeyModal] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [createdKey, setCreatedKey] = useState<string | null>(null);

  // Profile Test State
  const [testingProfileId, setTestingProfileId] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});
  const [testModalProfile, setTestModalProfile] = useState<Profile | null>(null);
  const [testModalPrompt, setTestModalPrompt] = useState("Hello! Introduce yourself in one short sentence.");
  const [testModel, setTestModel] = useState<string>("");
  const [testModalLoading, setTestModalLoading] = useState(false);
  const [testModalResult, setTestModalResult] = useState<TestResult | null>(null);
  const [showRawJson, setShowRawJson] = useState(false);
  const [copiedResponse, setCopiedResponse] = useState(false);




  const fetchHealth = async () => {
    try {
      const res = await fetch("/health");
      if (res.ok) setHealth(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchProfiles = async () => {
    try {
      const res = await fetch("/v1/profiles");
      if (res.ok) {
        const data = await res.json();
        setProfiles(data.profiles || data.data || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchKeys = async () => {
    try {
      const res = await fetch("/v1/keys");
      if (res.ok) {
        const data = await res.json();
        setKeys(data.keys || data.data || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const refreshAll = async () => {
    setLoading(true);
    await Promise.all([fetchHealth(), fetchProfiles(), fetchKeys()]);
    setLoading(false);
  };

  useEffect(() => {
    refreshAll();
  }, []);

  const handleCreateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload: any = {
        type: newProfileType,
        name: newProfileName,
        is_active: newProfileIsActive,
      };
      if (newProfileType === "deepseek") {
        payload.token = newProfileCredential;
      } else {
        payload.cookie = newProfileCredential;
      }

      const res = await fetch("/v1/profiles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        setShowAddProfileModal(false);
        setNewProfileName("");
        setNewProfileCredential("");
        setNewProfileIsActive(true);
        refreshAll();
      } else {
        const err = await res.json();
        alert(`Error: ${err.error?.message || "Failed to create profile"}`);
      }
    } catch (e: any) {
      alert(`Error: ${e.message}`);
    }
  };

  const handleToggleProfileActive = async (profile: Profile) => {
    try {
      const res = await fetch(`/v1/profiles/${profile.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: !profile.is_active }),
      });
      if (res.ok) {
        refreshAll();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const confirmDeleteProfile = async () => {
    if (!deletingProfile) return;
    try {
      const res = await fetch(`/v1/profiles/${deletingProfile.id}`, { method: "DELETE" });
      if (res.ok) {
        setDeletingProfile(null);
        refreshAll();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingProfile) return;
    try {
      const payload: any = { 
        name: editName,
        is_active: editIsActive
      };
      if (editCredential) {
        if (editingProfile.type === "deepseek") payload.token = editCredential;
        else payload.cookie = editCredential;
      }

      const res = await fetch(`/v1/profiles/${editingProfile.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        setEditingProfile(null);
        refreshAll();
      } else {
        const err = await res.json();
        alert(`Error: ${err.error?.message || "Failed to update"}`);
      }
    } catch (e: any) {
      alert(`Error: ${e.message}`);
    }
  };

  const handleTestProfile = async (profile: Profile, customMessage?: string, customModel?: string) => {
    setTestingProfileId(profile.id);
    setTestModalLoading(true);
    setCopiedResponse(false);
    const startT = Date.now();
    const defaultModel = profile.type === "deepseek" ? "deepseek-chat" : "gemini-3-flash";
    const selectedModel = customModel || testModel || defaultModel;
    const promptText = customMessage || "Hello! Reply with 'OK' if you can read this.";

    try {
      const res = await fetch(`/v1/${profile.type}/chat/completions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer dev-key",
          "X-Session-Id": `test-${profile.id}-${Date.now()}`
        },
        body: JSON.stringify({
          model: selectedModel,
          messages: [{ role: "user", content: promptText }],
          stream: false
        }),
      });

      const elapsed = Date.now() - startT;

      if (res.ok) {
        const data = await res.json();
        const replyText = data.choices?.[0]?.message?.content || "OK (No content returned)";
        const successResult: TestResult = {
          status: "ok",
          profile_id: profile.id,
          type: profile.type,
          model: selectedModel,
          latency_ms: elapsed,
          reply: replyText,
          rawJson: data
        };
        setTestResults((prev) => ({ ...prev, [profile.id]: successResult }));
        setTestModalResult(successResult);
        return successResult;
      } else {
        let errMessage = `HTTP ${res.status}: ${res.statusText}`;
        let errData: any = null;
        try {
          errData = await res.json();
          errMessage = errData.error?.message || errData.detail || JSON.stringify(errData);
        } catch {
          // ignore
        }
        const failResult: TestResult = {
          status: "error",
          profile_id: profile.id,
          type: profile.type,
          model: selectedModel,
          latency_ms: elapsed,
          error: errMessage,
          rawJson: errData || { status: res.status, statusText: res.statusText }
        };
        setTestResults((prev) => ({ ...prev, [profile.id]: failResult }));
        setTestModalResult(failResult);
        return failResult;
      }
    } catch (e: any) {
      const elapsed = Date.now() - startT;
      const networkErrorResult: TestResult = {
        status: "error",
        profile_id: profile.id,
        type: profile.type,
        model: selectedModel,
        latency_ms: elapsed,
        error: e?.message || "Network request failed",
        rawJson: { error: e?.message || "Network request failed" }
      };
      setTestResults((prev) => ({ ...prev, [profile.id]: networkErrorResult }));
      setTestModalResult(networkErrorResult);
      return networkErrorResult;
    } finally {
      setTestingProfileId(null);
      setTestModalLoading(false);
    }
  };

  const openTestModal = (profile: Profile) => {
    setTestModalProfile(profile);
    const initialModel = profile.type === "deepseek" ? "deepseek-chat" : "gemini-3-flash";
    setTestModel(initialModel);
    setShowRawJson(false);
    setCopiedResponse(false);
    const existing = testResults[profile.id];
    setTestModalResult(existing || null);
    if (!existing) {
      handleTestProfile(profile, testModalPrompt, initialModel);
    }
  };




  const handleCreateKey = async (e: React.FormEvent) => {

    e.preventDefault();
    try {
      const res = await fetch("/v1/keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newKeyName }),
      });
      if (res.ok) {
        const data = await res.json();
        setCreatedKey(data.key);
        setNewKeyName("");
        fetchKeys();
      }
    } catch (e: any) {
      alert(`Error: ${e.message}`);
    }
  };

  const handleDeleteKey = async (keyId: string) => {
    if (!confirm("Are you sure you want to delete this API key?")) return;
    try {
      const res = await fetch(`/v1/keys/${keyId}`, { method: "DELETE" });
      if (res.ok) fetchKeys();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      {/* Top Navbar */}
      <nav className="border-b border-border bg-card/60 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-muted rounded-xl border border-border">
              <Zap className="w-5 h-5 text-foreground" />
            </div>
            <div>
              <h1 className="font-bold text-lg tracking-tight text-foreground">
                Unofficial API Gateway
              </h1>
              <p className="text-xs text-muted-foreground">Multi-Profile Load Balancer Management</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="icon"
              onClick={refreshAll}
              disabled={loading}
              title="Refresh Data"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
            <a
              href="/docs"
              target="_blank"
              rel="noreferrer"
            >
              <Button variant="secondary" size="sm" className="gap-1.5 text-xs">
                <span>Swagger API Docs</span>
                <ExternalLink className="w-3 h-3" />
              </Button>
            </a>
          </div>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Status Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardDescription className="uppercase tracking-wider">Gateway Health</CardDescription>
              <div className="p-2 bg-muted rounded-xl border border-border">
                <Activity className="w-5 h-5 text-foreground" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <span className="relative flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                </span>
                <span className="text-xl font-bold text-foreground">
                  {health?.status === "ok" ? "Operational" : "Checking..."}
                </span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardDescription className="uppercase tracking-wider">DeepSeek Active Profiles</CardDescription>
              <div className="p-2 bg-muted rounded-xl border border-border">
                <Database className="w-5 h-5 text-foreground" />
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-foreground">
                {health?.deepseek_active_profiles ?? 0}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardDescription className="uppercase tracking-wider">Gemini Active Profiles</CardDescription>
              <div className="p-2 bg-muted rounded-xl border border-border">
                <Globe className="w-5 h-5 text-foreground" />
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-foreground">
                {health?.gemini_active_profiles ?? 0}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Tab Selection */}
        <div className="flex items-center justify-between border-b border-border pb-4 mb-6">
          <div className="flex gap-2">
            <Button
              variant={activeTab === "profiles" ? "default" : "ghost"}
              onClick={() => setActiveTab("profiles")}
              className="gap-2"
            >
              <Shield className="w-4 h-4" />
              <span>Profiles Management</span>
              <Badge variant="secondary" className="ml-1">
                {profiles.length}
              </Badge>
            </Button>
            <Button
              variant={activeTab === "keys" ? "default" : "ghost"}
              onClick={() => setActiveTab("keys")}
              className="gap-2"
            >
              <Key className="w-4 h-4" />
              <span>API Keys</span>
              <Badge variant="secondary" className="ml-1">
                {keys.length}
              </Badge>
            </Button>
          </div>

          {activeTab === "profiles" ? (
            <Button onClick={() => setShowAddProfileModal(true)} className="gap-2">
              <Plus className="w-4 h-4" />
              <span>Add Profile</span>
            </Button>
          ) : (
            <Button onClick={() => setShowAddKeyModal(true)} className="gap-2">
              <Plus className="w-4 h-4" />
              <span>Generate API Key</span>
            </Button>
          )}
        </div>

        {/* Profiles Table View (shadcn/ui Table) */}
        {activeTab === "profiles" && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Provider Profiles Table</CardTitle>
              <CardDescription>Manage credential profiles for DeepSeek and Gemini load balancers</CardDescription>
            </CardHeader>
            <CardContent>
              {profiles.length === 0 ? (
                <div className="text-center py-12">
                  <Shield className="w-12 h-12 text-muted-foreground mx-auto mb-3" />
                  <p className="text-muted-foreground text-sm mb-4">No profiles found.</p>
                  <Button variant="outline" onClick={() => setShowAddProfileModal(true)}>
                    Create Your First Profile
                  </Button>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[110px]">Type</TableHead>
                      <TableHead>Profile Info</TableHead>
                      <TableHead className="w-[120px]">Requests</TableHead>
                      <TableHead className="w-[130px]">Active Status</TableHead>
                      <TableHead className="w-[170px]">Test Connection</TableHead>
                      <TableHead className="w-[160px]">Updated At</TableHead>
                      <TableHead className="text-right w-[100px]">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {profiles.map((p) => (
                      <TableRow key={p.id} className={!p.is_active ? "opacity-75" : ""}>
                        <TableCell>
                          <Badge variant="secondary" className="uppercase tracking-wider font-bold">
                            {p.type}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="font-semibold text-foreground">{p.name}</div>
                          <div className="text-xs font-mono text-muted-foreground">ID: {p.id}</div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1.5">
                            <span className="font-mono text-sm font-semibold text-foreground">
                              {p.total_requests || 0}
                            </span>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => setViewStatsProfile(p)}
                              className="h-7 w-7 text-muted-foreground hover:text-primary hover:bg-primary/10"
                              title="View Hourly Request Statistics"
                            >
                              <Activity className="w-3.5 h-3.5" />
                            </Button>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Switch
                              checked={p.is_active}
                              onCheckedChange={() => handleToggleProfileActive(p)}
                            />
                            <span className={`text-xs font-medium ${p.is_active ? "text-emerald-400" : "text-muted-foreground"}`}>
                              {p.is_active ? "Active" : "Inactive"}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={testingProfileId === p.id}
                              onClick={() => openTestModal(p)}
                              className="h-7 px-2.5 text-xs gap-1.5 font-medium border-border hover:bg-primary/10 hover:text-primary transition-all"
                              title="Test connectivity and view full response"
                            >
                              {testingProfileId === p.id ? (
                                <Loader2 className="w-3 h-3 animate-spin text-primary" />
                              ) : (
                                <Play className="w-3 h-3 text-primary fill-primary/20" />
                              )}
                              <span>{testingProfileId === p.id ? "Testing..." : "Test"}</span>
                            </Button>

                            {testResults[p.id] && (
                              <button
                                onClick={() => openTestModal(p)}
                                className="cursor-pointer group flex items-center"
                                title="Click to view full test response details"
                              >
                                {testResults[p.id].status === "ok" ? (
                                  <Badge
                                    variant="outline"
                                    className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 gap-1 text-[11px] py-0.5 px-2 font-mono group-hover:border-emerald-500/50 transition-colors"
                                  >
                                    <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                                    <span>{testResults[p.id].latency_ms}ms</span>
                                  </Badge>
                                ) : (
                                  <Badge
                                    variant="outline"
                                    className="bg-destructive/10 text-destructive border-destructive/20 gap-1 text-[11px] py-0.5 px-2 font-mono group-hover:border-destructive/50 transition-colors"
                                  >
                                    <XCircle className="w-3 h-3 text-destructive" />
                                    <span>Failed</span>
                                  </Badge>
                                )}
                              </button>
                            )}
                          </div>
                        </TableCell>

                        <TableCell className="text-xs text-muted-foreground">
                          {p.updated_at ? new Date(p.updated_at).toLocaleString() : "N/A"}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => {
                                setEditingProfile(p);
                                setEditName(p.name);
                                setEditIsActive(p.is_active);
                                setEditCredential("");
                              }}
                              title="Edit Profile"
                            >
                              <Edit2 className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => setDeletingProfile(p)}
                              className="text-destructive hover:bg-destructive/10"
                              title="Delete Profile"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>

                </Table>
              )}
            </CardContent>
          </Card>
        )}

        {/* API Keys View */}
        {activeTab === "keys" && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Configured API Keys</CardTitle>
              <CardDescription>Generate keys for managing authentication</CardDescription>
            </CardHeader>
            <CardContent>
              {keys.length === 0 ? (
                <p className="text-xs text-muted-foreground">No custom API keys generated yet.</p>
              ) : (
                <div className="divide-y divide-border">
                  {keys.map((k) => (
                    <div key={k.id} className="py-4 flex items-center justify-between">
                      <div>
                        <p className="font-medium text-sm text-foreground">{k.name}</p>
                        <p className="text-xs font-mono text-muted-foreground mt-0.5">
                          Prefix: <span className="text-foreground">{k.prefix || k.id}</span>
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDeleteKey(k.id)}
                        className="text-destructive hover:bg-destructive/10"
                        title="Revoke Key"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </main>

      {/* View Request Statistics Modal */}
      {viewStatsProfile && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <Card className="max-w-lg w-full max-h-[85vh] flex flex-col p-2">
            <CardHeader className="flex flex-row items-center justify-between pb-2 border-b border-border/40">
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Activity className="w-5 h-5 text-primary" />
                  Thống kê Request
                </CardTitle>
                <CardDescription className="text-xs font-mono mt-0.5">{viewStatsProfile.name} ({viewStatsProfile.id})</CardDescription>
              </div>
              <Badge variant="secondary" className="font-mono text-xs px-2.5 py-1">
                Tổng: {viewStatsProfile.total_requests || 0}
              </Badge>
            </CardHeader>
            <CardContent className="overflow-y-auto space-y-4 pt-4 flex-1">
              {(!viewStatsProfile.request_counts || Object.keys(viewStatsProfile.request_counts).length === 0) ? (
                <div className="text-center py-8">
                  <Activity className="w-10 h-10 text-muted-foreground mx-auto mb-2 opacity-50" />
                  <p className="text-sm text-muted-foreground">Chưa có dữ liệu request cho profile này.</p>
                </div>
              ) : (
                Object.entries(viewStatsProfile.request_counts)
                  .sort(([d1], [d2]) => d2.localeCompare(d1))
                  .map(([date, hours]) => {
                    const dayTotal = Object.values(hours).reduce((a, b) => a + b, 0);
                    return (
                      <div key={date} className="border border-border/80 rounded-xl p-3 bg-muted/20 space-y-2">
                        <div className="flex items-center justify-between font-semibold text-xs text-foreground border-b border-border/40 pb-2">
                          <span>📅 Ngày {date}</span>
                          <Badge variant="outline" className="text-[11px] font-mono">Lượt gọi ngày: {dayTotal}</Badge>
                        </div>
                        <div className="grid grid-cols-4 sm:grid-cols-6 gap-2 pt-1">
                          {Object.entries(hours)
                            .sort(([h1], [h2]) => h1.localeCompare(h2))
                            .map(([hour, count]) => (
                              <div key={hour} className="bg-background border border-border/60 rounded-lg p-2 text-center shadow-xs">
                                <div className="text-[10px] text-muted-foreground font-mono">{hour}:00</div>
                                <div className="text-sm font-bold text-primary">{count}</div>
                              </div>
                            ))}
                        </div>
                      </div>
                    );
                  })
              )}
            </CardContent>
            <div className="flex justify-end pt-3 pb-1 px-4 border-t border-border/40">
              <Button variant="outline" size="sm" onClick={() => setViewStatsProfile(null)}>
                Đóng
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* Confirm Delete Profile Modal */}
      {deletingProfile && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <Card className="max-w-md w-full p-2">
            <CardHeader className="flex flex-row items-center gap-3 pb-2">
              <div className="p-2.5 bg-destructive/10 text-destructive rounded-xl border border-destructive/20">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <CardTitle className="text-lg">Xác nhận xoá Profile</CardTitle>
                <CardDescription>Hành động này không thể hoàn tác</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-foreground">
                Bạn có chắc chắn muốn xoá Profile <strong className="text-foreground">{deletingProfile.name}</strong> (<code className="text-xs font-mono bg-muted px-1.5 py-0.5 rounded">{deletingProfile.id}</code>) không?
              </p>

              <div className="flex items-center justify-end gap-3 pt-2">
                <Button type="button" variant="ghost" onClick={() => setDeletingProfile(null)}>
                  Hủy bỏ
                </Button>
                <Button variant="destructive" onClick={confirmDeleteProfile}>
                  Xoá Profile
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Add Profile Modal */}
      {showAddProfileModal && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <Card className="max-w-md w-full p-2">
            <CardHeader>
              <CardTitle className="text-lg">Add Provider Profile</CardTitle>
              <CardDescription>Configure credentials for DeepSeek or Gemini</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreateProfile} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1.5">Provider Type</label>
                  <select
                    value={newProfileType}
                    onChange={(e) => setNewProfileType(e.target.value as any)}
                    className="w-full bg-background border border-input rounded-xl px-3.5 py-2.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                  >
                    <option value="deepseek">DeepSeek</option>
                    <option value="gemini">Gemini</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1.5">Profile Name</label>
                  <Input
                    type="text"
                    placeholder="e.g. DeepSeek Account 1"
                    value={newProfileName}
                    onChange={(e) => setNewProfileName(e.target.value)}
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                    {newProfileType === "deepseek" ? "DeepSeek Auth Token (Bearer token)" : "Gemini Cookie Header String"}
                  </label>
                  <Textarea
                    rows={3}
                    placeholder={newProfileType === "deepseek" ? "Bearer M3KFWf..." : "SAPISID=...; __Secure-1PSID=..."}
                    value={newProfileCredential}
                    onChange={(e) => setNewProfileCredential(e.target.value)}
                    required
                  />
                </div>

                <div className="flex items-center justify-between pt-2">
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={newProfileIsActive}
                      onCheckedChange={(checked) => setNewProfileIsActive(!!checked)}
                    />
                    <span className="text-xs text-muted-foreground">Active Status</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button type="button" variant="ghost" onClick={() => setShowAddProfileModal(false)}>
                      Cancel
                    </Button>
                    <Button type="submit">
                      Save Profile
                    </Button>
                  </div>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Edit Profile Modal */}
      {editingProfile && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <Card className="max-w-md w-full p-2">
            <CardHeader>
              <CardTitle className="text-lg">Edit Profile</CardTitle>
              <CardDescription>ID: {editingProfile.id}</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleUpdateProfile} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1.5">Profile Name</label>
                  <Input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                    Update {editingProfile.type === "deepseek" ? "Token" : "Cookie"} (Leave blank to keep unchanged)
                  </label>
                  <Textarea
                    rows={3}
                    placeholder="Paste new credential to update..."
                    value={editCredential}
                    onChange={(e) => setEditCredential(e.target.value)}
                  />
                </div>

                <div className="flex items-center justify-between pt-2">
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={editIsActive}
                      onCheckedChange={(checked) => setEditIsActive(!!checked)}
                    />
                    <span className="text-xs text-muted-foreground">
                      {editIsActive ? "Active" : "Inactive"}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button type="button" variant="ghost" onClick={() => setEditingProfile(null)}>
                      Cancel
                    </Button>
                    <Button type="submit">
                      Update Profile
                    </Button>
                  </div>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Generate API Key Modal */}
      {showAddKeyModal && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <Card className="max-w-md w-full p-2">
            <CardHeader>
              <CardTitle className="text-lg">Generate New API Key</CardTitle>
            </CardHeader>
            <CardContent>
              {createdKey ? (
                <div>
                  <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl mb-4 text-xs font-mono text-emerald-400 break-all">
                    <p className="font-bold mb-1">API Key Generated! Copy it now:</p>
                    <p className="text-foreground text-sm select-all">{createdKey}</p>
                  </div>
                  <Button
                    className="w-full"
                    onClick={() => {
                      setShowAddKeyModal(false);
                      setCreatedKey(null);
                    }}
                  >
                    Done
                  </Button>
                </div>
              ) : (
                <form onSubmit={handleCreateKey} className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1.5">Key Description / Name</label>
                    <Input
                      type="text"
                      placeholder="e.g. Production Key"
                      value={newKeyName}
                      onChange={(e) => setNewKeyName(e.target.value)}
                      required
                    />
                  </div>
                  <div className="flex items-center justify-end gap-3 pt-3">
                    <Button type="button" variant="ghost" onClick={() => setShowAddKeyModal(false)}>
                      Cancel
                    </Button>
                    <Button type="submit">
                      Generate
                    </Button>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>
        </div>
      )}
      {/* Test Profile Modal */}
      {testModalProfile && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <Card className="max-w-2xl w-full p-2 max-h-[90vh] flex flex-col">
            <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-border">
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-primary" />
                  <span>Test Profile: {testModalProfile.name}</span>
                </CardTitle>
                <CardDescription className="flex items-center gap-2 mt-1">
                  <Badge variant="secondary" className="uppercase font-bold text-[10px]">
                    {testModalProfile.type}
                  </Badge>
                  <span className="text-xs font-mono text-muted-foreground">ID: {testModalProfile.id}</span>
                  <span className="text-xs text-muted-foreground">• Model: <code className="text-foreground">{testModel || (testModalProfile.type === "deepseek" ? "deepseek-chat" : "gemini-3-flash")}</code></span>
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-4 pt-4 overflow-y-auto flex-1">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="sm:col-span-1">
                  <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                    Model
                  </label>
                  <select
                    value={testModel}
                    onChange={(e) => setTestModel(e.target.value)}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring font-mono"
                  >
                    {testModalProfile.type === "deepseek" ? (
                      <>
                        <option value="deepseek-chat">deepseek-chat (Default)</option>
                        <option value="deepseek-v3">deepseek-v3</option>
                        <option value="deepseek-r1">deepseek-r1</option>
                      </>
                    ) : (
                      <>
                        <option value="gemini-3-flash">gemini-3-flash (Default)</option>
                        <option value="gemini-3-pro">gemini-3-pro</option>
                        <option value="gemini-3-flash-thinking">gemini-3-flash-thinking</option>
                        <option value="gemini-3-flash-advanced">gemini-3-flash-advanced</option>
                        <option value="gemini-3-pro-advanced">gemini-3-pro-advanced</option>
                      </>
                    )}
                  </select>
                </div>

                <div className="sm:col-span-2">
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="block text-xs font-medium text-muted-foreground">
                      Test Prompt
                    </label>
                    <div className="flex items-center gap-1">
                      <span className="text-[11px] text-muted-foreground mr-1">Presets:</span>
                      <button
                        type="button"
                        onClick={() => setTestModalPrompt("Hello! Reply with 'OK' if you can read this.")}
                        className="text-[11px] bg-muted px-2 py-0.5 rounded-md hover:bg-muted-foreground/20 text-muted-foreground hover:text-foreground transition cursor-pointer"
                      >
                        Ping
                      </button>
                      <button
                        type="button"
                        onClick={() => setTestModalPrompt("What is 15 + 27? Reply with only the number.")}
                        className="text-[11px] bg-muted px-2 py-0.5 rounded-md hover:bg-muted-foreground/20 text-muted-foreground hover:text-foreground transition cursor-pointer"
                      >
                        Math
                      </button>
                      <button
                        type="button"
                        onClick={() => setTestModalPrompt("Introduce yourself in 10 words or less.")}
                        className="text-[11px] bg-muted px-2 py-0.5 rounded-md hover:bg-muted-foreground/20 text-muted-foreground hover:text-foreground transition cursor-pointer"
                      >
                        Intro
                      </button>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Input
                      type="text"
                      value={testModalPrompt}
                      onChange={(e) => setTestModalPrompt(e.target.value)}
                      placeholder="Enter test prompt..."
                      className="text-sm font-sans"
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !testModalLoading) {
                          e.preventDefault();
                          handleTestProfile(testModalProfile, testModalPrompt, testModel);
                        }
                      }}
                    />
                    <Button
                      disabled={testModalLoading}
                      onClick={() => handleTestProfile(testModalProfile, testModalPrompt, testModel)}
                      className="gap-1.5 shrink-0"
                    >
                      {testModalLoading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Play className="w-4 h-4 fill-current" />
                      )}
                      <span>{testModalLoading ? "Testing..." : "Run Test"}</span>
                    </Button>
                  </div>
                </div>
              </div>


              {/* Response Section */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-muted-foreground flex items-center gap-1.5">
                    <MessageSquare className="w-3.5 h-3.5" />
                    <span>Response from AI Model:</span>
                  </span>

                  {testModalResult && !testModalLoading && (
                    <div className="flex items-center gap-2">
                      <div className="flex items-center bg-muted/60 p-0.5 rounded-lg border border-border">
                        <button
                          type="button"
                          onClick={() => setShowRawJson(false)}
                          className={`px-2 py-0.5 text-[11px] rounded font-medium transition ${
                            !showRawJson ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                          }`}
                        >
                          Text
                        </button>
                        <button
                          type="button"
                          onClick={() => setShowRawJson(true)}
                          className={`px-2 py-0.5 text-[11px] rounded font-medium transition flex items-center gap-1 ${
                            showRawJson ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                          }`}
                        >
                          <Code className="w-3 h-3" />
                          <span>JSON</span>
                        </button>
                      </div>

                      <button
                        type="button"
                        onClick={() => {
                          const textToCopy = showRawJson 
                            ? JSON.stringify(testModalResult.rawJson, null, 2)
                            : (testModalResult.reply || testModalResult.error || "");
                          navigator.clipboard.writeText(textToCopy);
                          setCopiedResponse(true);
                          setTimeout(() => setCopiedResponse(false), 2000);
                        }}
                        className="flex items-center gap-1 text-[11px] px-2 py-0.5 rounded bg-muted hover:bg-muted-foreground/20 text-muted-foreground hover:text-foreground transition cursor-pointer"
                        title="Copy to clipboard"
                      >
                        {copiedResponse ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        <span>{copiedResponse ? "Copied!" : "Copy"}</span>
                      </button>

                      <div className="flex items-center gap-1.5 font-mono ml-1">
                        {testModalResult.status === "ok" ? (
                          <Badge variant="outline" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[11px] py-0 px-1.5 gap-1">
                            <CheckCircle2 className="w-3 h-3" /> 200 OK
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="bg-destructive/10 text-destructive border-destructive/20 text-[11px] py-0 px-1.5 gap-1">
                            <XCircle className="w-3 h-3" /> Error
                          </Badge>
                        )}
                        <span className="text-muted-foreground flex items-center gap-1 text-[11px]">
                          <Clock className="w-3 h-3" /> {testModalResult.latency_ms}ms
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                {testModalLoading ? (
                  <div className="p-8 border border-border rounded-xl bg-muted/20 flex flex-col items-center justify-center gap-2 text-muted-foreground">
                    <Loader2 className="w-6 h-6 animate-spin text-primary" />
                    <p className="text-xs">Sending prompt to profile and waiting for response...</p>
                  </div>
                ) : testModalResult ? (
                  showRawJson ? (
                    <pre className="p-3.5 rounded-xl border bg-muted/60 border-border text-xs font-mono overflow-auto max-h-72 select-text leading-relaxed">
                      {JSON.stringify(testModalResult.rawJson || testModalResult, null, 2)}
                    </pre>
                  ) : (
                    <div className={`p-4 rounded-xl border text-sm leading-relaxed overflow-auto max-h-72 select-text ${
                      testModalResult.status === "ok"
                        ? "bg-muted/40 border-border text-foreground font-sans"
                        : "bg-destructive/10 border-destructive/20 text-destructive font-mono text-xs"
                    }`}>
                      {testModalResult.status === "ok" ? (
                        <p className="whitespace-pre-wrap">{testModalResult.reply || "No text content in response."}</p>
                      ) : (
                        <div className="space-y-1">
                          <p className="font-bold">Error testing profile:</p>
                          <p className="whitespace-pre-wrap">{testModalResult.error || "Unknown failure"}</p>
                        </div>
                      )}
                    </div>
                  )
                ) : (
                  <div className="p-6 border border-dashed border-border rounded-xl text-center text-xs text-muted-foreground">
                    Click <strong>"Run Test"</strong> above to send a test request and view the response.
                  </div>
                )}
              </div>

              <div className="flex justify-end pt-2 border-t border-border">
                <Button variant="ghost" onClick={() => setTestModalProfile(null)}>
                  Close
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

    </div>
  );
}

export default App;

