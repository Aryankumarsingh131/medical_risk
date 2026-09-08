import React, { createContext, useContext, useState } from "react";
import { apiRequest } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(() => {
    const saved = localStorage.getItem("medrisk_auth");
    return saved ? JSON.parse(saved) : null;
  });

  const login = async (email, password, hospitalCode) => {
    const body = { email, password };
    if (hospitalCode) body.hospital_code = hospitalCode;
    const data = await apiRequest("/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    });
    setAuth(data);
    localStorage.setItem("medrisk_auth", JSON.stringify(data));
    return data;
  };

  const register = async (payload) => {
    const data = await apiRequest("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setAuth(data);
    localStorage.setItem("medrisk_auth", JSON.stringify(data));
    return data;
  };

  const logout = () => {
    setAuth(null);
    localStorage.removeItem("medrisk_auth");
  };

  return (
    <AuthContext.Provider value={{ auth, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
