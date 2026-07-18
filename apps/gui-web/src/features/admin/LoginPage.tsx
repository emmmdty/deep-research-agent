import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { LogIn } from "lucide-react";

import { productApi } from "../../api/client";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const navigate = useNavigate();
  return <main className="login-page"><form onSubmit={async (event) => { event.preventDefault(); setPending(true); setError(""); try { await productApi.login(email, password); navigate("/topics"); } catch (caught) { setError(caught instanceof Error ? caught.message : "登录失败"); } finally { setPending(false); } }}>
    <span className="wordmark-mark">ER</span><span className="section-label">Evidence Research</span><h1>进入研究工作区</h1>
    <label htmlFor="email">邮箱</label><input autoComplete="email" id="email" onChange={(event) => setEmail(event.target.value)} type="email" value={email} />
    <label htmlFor="password">密码</label><input autoComplete="current-password" id="password" onChange={(event) => setPassword(event.target.value)} type="password" value={password} />
    <button className="primary-button" disabled={pending || !email || !password} type="submit">登录 <LogIn size={16} /></button>
    {error ? <p className="form-error" role="alert">{error}</p> : null}
  </form></main>;
}
