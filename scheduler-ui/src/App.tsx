import { Routes, Route, Navigate } from "react-router-dom";
import { useEffect } from "react";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
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
      {/* Default redirect */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      {/* Protected Dashboard */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />

      {/* Public Routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
    </Routes>
  );
};

const App = () => (
  <AuthProvider>
    <AppRoutes />
  </AuthProvider>
);

export default App;
