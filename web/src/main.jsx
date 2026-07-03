import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Analytics } from "@vercel/analytics/react";
import App from "./App.jsx";
import Login from "./pages/Login.jsx";
import Signup from "./pages/Signup.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Admin from "./pages/Admin.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/"          element={<App />} />
        <Route path="/login"     element={<Login />} />
        <Route path="/signup"    element={<Signup />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/admin"     element={<Admin />} />
      </Routes>
      <Analytics />
    </BrowserRouter>
  </StrictMode>
);
