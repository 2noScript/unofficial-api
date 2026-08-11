import React, { useState, useEffect } from "react";
import { 
  Shield, 
  Key, 
  Plus, 
  Trash2, 
  RefreshCw, 
  CheckCircle2, 
  XCircle, 
  Activity, 
  ExternalLink,
  Edit2,
  Zap,
  Globe,
  Database
} from "lucide-react";

import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

interface Profile {
  id: string;
  type: "deepseek" | "gemini";
  name: string;
  token?: string | null;
  cookie?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
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

  // Edit Profile Modal State
  const [editingProfile, setEditingProfile] = useState<Profile | null>(null);
  const [editName, setEditName] = useState("");
  const [editCredential, setEditCredential] = useState("");

  // New Key Modal State
  const [showAddKeyModal, setShowAddKeyModal] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [createdKey, setCreatedKey] = useState<string | null>(null);

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
        is_active: true,
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

  const handleDeleteProfile = async (profileId: string) => {
    if (!confirm("Are you sure you want to delete this profile?")) return;
    try {
      const res = await fetch(`/v1/profiles/${profileId}`, { method: "DELETE" });
      if (res.ok) refreshAll();
    } catch (e) {
      console.error(e);
    }
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingProfile) return;
    try {
      const payload: any = { name: editName };
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

        {/* Profiles View */}
        {activeTab === "profiles" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {profiles.length === 0 ? (
              <Card className="col-span-2 text-center py-16">
                <CardContent className="flex flex-col items-center">
                  <Shield className="w-12 h-12 text-muted-foreground mb-3" />
                  <p className="text-muted-foreground text-sm mb-4">No profiles found.</p>
                  <Button variant="outline" onClick={() => setShowAddProfileModal(true)}>
                    Create Your First Profile
                  </Button>
                </CardContent>
              </Card>
            ) : (
              profiles.map((p) => (
                <Card
                  key={p.id}
                  className={`transition-all ${!p.is_active && "border-destructive/40 opacity-75"}`}
                >
                  <CardHeader className="flex flex-row items-start justify-between pb-3">
                    <div>
                      <div className="flex items-center gap-2.5 mb-1">
                        <Badge variant="secondary">
                          {p.type}
                        </Badge>
                        <CardTitle className="text-base">{p.name}</CardTitle>
                      </div>
                      <CardDescription className="font-mono">
                        ID: {p.id}
                      </CardDescription>
                    </div>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleToggleProfileActive(p)}
                      className={`gap-1.5 text-xs ${
                        p.is_active
                          ? "border-emerald-800/40 text-emerald-400 hover:bg-emerald-950/40"
                          : "border-destructive/40 text-destructive hover:bg-destructive/10"
                      }`}
                    >
                      {p.is_active ? (
                        <>
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Active</span>
                        </>
                      ) : (
                        <>
                          <XCircle className="w-3.5 h-3.5" />
                          <span>Inactive</span>
                        </>
                      )}
                    </Button>
                  </CardHeader>

                  <CardContent className="space-y-4">
                    <div className="bg-muted/60 border border-border rounded-xl p-3 text-xs font-mono text-muted-foreground truncate">
                      <span className="text-foreground mr-2 font-semibold">
                        {p.type === "deepseek" ? "TOKEN:" : "COOKIE:"}
                      </span>
                      {p.type === "deepseek"
                        ? p.token ? `${p.token.slice(0, 16)}...` : "None"
                        : p.cookie ? `${p.cookie.slice(0, 24)}...` : "None"}
                    </div>

                    <div className="flex items-center justify-between pt-3 border-t border-border text-xs text-muted-foreground">
                      <span>Updated: {p.updated_at ? new Date(p.updated_at).toLocaleString() : "N/A"}</span>

                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => {
                            setEditingProfile(p);
                            setEditName(p.name);
                            setEditCredential("");
                          }}
                          title="Edit Profile"
                        >
                          <Edit2 className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDeleteProfile(p.id)}
                          className="text-destructive hover:bg-destructive/10"
                          title="Delete Profile"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
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

                <div className="flex items-center justify-end gap-3 pt-3">
                  <Button type="button" variant="ghost" onClick={() => setShowAddProfileModal(false)}>
                    Cancel
                  </Button>
                  <Button type="submit">
                    Save Profile
                  </Button>
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

                <div className="flex items-center justify-end gap-3 pt-3">
                  <Button type="button" variant="ghost" onClick={() => setEditingProfile(null)}>
                    Cancel
                  </Button>
                  <Button type="submit">
                    Update Profile
                  </Button>
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
    </div>
  );
}

export default App;
