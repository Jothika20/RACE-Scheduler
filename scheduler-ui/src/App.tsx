import { Routes, Route, Navigate } from "react-router-dom";
import { useEffect } from "react";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Home from "./pages/Home";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { attachLogoutInterceptor } from "./api/axios";
import { message } from "antd";
import ProtectedRoute from "./ProtectedRoute";

message.config({
  top: 80,
  duration: 3,
  maxCount: 3,
});

const AppRoutes = () => {
  const { token, logout } = useAuth();

  useEffect(() => {
    attachLogoutInterceptor(logout);
  }, [logout]);

  return (
    <Routes>
      {/* Public Home */}
      <Route
        path="/"
        element={token ? <Navigate to="/dashboard" replace /> : <Home />}
      />

      {/* Public Auth Routes */}
      <Route
        path="/login"
        element={token ? <Navigate to="/dashboard" replace /> : <Login />}
      />
      <Route
        path="/register"
        element={token ? <Navigate to="/dashboard" replace /> : <Register />}
      />

      {/* Protected Dashboard */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
};

const App = () => (
  <AuthProvider>
    <AppRoutes />
  </AuthProvider>
);

export default App;
