import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import ScanUpload from "./pages/ScanUpload";
import ScanDetail from "./pages/ScanDetail";
import Repository from "./pages/Repository";
import Users from "./pages/Users";

function Protected({ children, roles }) {
  return (
    <ProtectedRoute roles={roles}>
      <Layout>{children}</Layout>
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Protected><Dashboard /></Protected>} />
      <Route path="/scan" element={<Protected><ScanUpload /></Protected>} />
      <Route path="/scans/:id" element={<Protected><ScanDetail /></Protected>} />
      <Route path="/repository" element={<Protected><Repository /></Protected>} />
      <Route
        path="/users"
        element={
          <Protected roles={["admin"]}>
            <Users />
          </Protected>
        }
      />
    </Routes>
  );
}
