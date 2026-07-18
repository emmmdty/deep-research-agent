import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";
import { LogIn, UserPlus } from "lucide-react";

import { productApi } from "../../api/client";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [mode, setMode] = useState<"login" | "register">("login");
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const destination = (location.state as { from?: string } | null)?.from ?? "/topics";
  const registration = useQuery({ queryKey: ["registration-status"], queryFn: () => productApi.registrationStatus() });
  const registrationEnabled = registration.data?.enabled ?? false;
  const isRegistering = mode === "register" && registrationEnabled;
  return <main className="login-page"><form onSubmit={async (event) => { event.preventDefault(); setPending(true); setError(""); try { const result = isRegistering ? await productApi.register(email, password) : await productApi.login(email, password); queryClient.setQueryData(["session"], { user: result.user }); await queryClient.invalidateQueries({ queryKey: ["session"] }); navigate(destination, { replace: true }); } catch (caught) { setError(caught instanceof Error ? caught.message : (isRegistering ? "注册失败" : "登录失败")); } finally { setPending(false); } }}>
    <span className="wordmark-mark">ER</span><span className="section-label">Evidence Research</span><h1>{isRegistering ? "创建研究账号" : "进入研究工作区"}</h1>
    <label htmlFor="email">邮箱</label><input autoComplete="email" id="email" onChange={(event) => setEmail(event.target.value)} type="email" value={email} />
    <label htmlFor="password">密码</label><input autoComplete={isRegistering ? "new-password" : "current-password"} id="password" minLength={isRegistering ? 12 : 1} onChange={(event) => setPassword(event.target.value)} type="password" value={password} />
    <button className="primary-button" disabled={pending || !email || !password} type="submit">{isRegistering ? "注册并进入" : "登录"} {isRegistering ? <UserPlus size={16} /> : <LogIn size={16} />}</button>
    {registrationEnabled ? <button className="auth-mode-button" onClick={() => { setMode(isRegistering ? "login" : "register"); setError(""); }} type="button">{isRegistering ? <><LogIn size={15} /> 返回登录</> : <><UserPlus size={15} /> 注册新账号</>}</button> : <p className="auth-note">当前环境使用邀请制账号。</p>}
    {isRegistering ? <p className="auth-note">本地 Demo 会为你创建独立工作区，密码至少 12 个字符。</p> : null}
    {error ? <p className="form-error" role="alert">{error}</p> : null}
  </form></main>;
}
