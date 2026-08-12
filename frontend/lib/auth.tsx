"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AuthUser, endpoints, setCsrfToken } from "./api";

type AuthContextValue = {
  user: AuthUser | null;
  loading: boolean;
  setUser: (user: AuthUser | null) => void;
  signOut: () => Promise<void>;
  can: (permission: string) => boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    endpoints
      .me()
      .then((res) => {
        // #region agent log
        fetch('http://127.0.0.1:7734/ingest/641bf763-dc10-4f7a-825b-05bd4821faeb',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'1d8612'},body:JSON.stringify({sessionId:'1d8612',runId:'post-fix',hypothesisId:'C',location:'auth.tsx:me:ok',message:'me succeeded',data:{userId:res.user?.id,hasCsrf:Boolean(res.csrf_token)},timestamp:Date.now()})}).catch(()=>{});
        // #endregion
        setCsrfToken(res.csrf_token);
        setUser(res.user);
      })
      .catch((err) => {
        // #region agent log
        fetch('http://127.0.0.1:7734/ingest/641bf763-dc10-4f7a-825b-05bd4821faeb',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'1d8612'},body:JSON.stringify({sessionId:'1d8612',runId:'post-fix',hypothesisId:'C',location:'auth.tsx:me:fail',message:'me failed -> user null',data:{status:err?.status,message:String(err?.message||err)},timestamp:Date.now()})}).catch(()=>{});
        // #endregion
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      setUser,
      signOut: async () => {
        await endpoints.logout().catch(() => undefined);
        setUser(null);
        router.push("/login");
      },
      can: (permission: string) => {
        if (!user) return false;
        return user.permissions.includes("*") || user.permissions.includes(permission);
      },
    }),
    [user, loading, router],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
