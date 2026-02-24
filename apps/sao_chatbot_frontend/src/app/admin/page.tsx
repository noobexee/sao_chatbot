"use client";

import { useEffect, useState } from "react";
import {getAllUsers} from "@/libs/auth/getUser";
import { createUser } from "@/libs/auth/newUser";
import { deleteUser } from "@/libs/auth/deleteUser";
import { updateUser } from "@/libs/auth/editUser";


interface User {
  id: string;
  username: string;
  role: string;
  is_active?: boolean;
}

export default function AdminPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("user");

  const [editingUserId, setEditingUserId] = useState<string | null>(null);

  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") || "" : "";

  // ===== LOAD USERS =====
  const loadUsers = async () => {
    try {
      setLoading(true);
      const data = await getAllUsers(token);
      setUsers(data);
    } catch {
      showMessage("Failed to load users");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  // ===== MESSAGE =====
  const showMessage = (msg: string) => {
    setMessage(msg);
    setTimeout(() => setMessage(""), 2500);
  };

  // ===== CREATE / UPDATE =====
  const handleSubmit = async () => {
    try {
      if (!username || !password) {
        showMessage("Username & password required");
        return;
      }

      if (editingUserId) {
        await updateUser(editingUserId, username, password, role, token);
        showMessage("User updated");
      } else {
        await createUser(username, password, role, token);
        showMessage("User created");
      }

      setUsername("");
      setPassword("");
      setRole("user");
      setEditingUserId(null);

      await loadUsers();
    } catch {
      showMessage("Action failed");
    }
  };

  // ===== DELETE =====
  const handleDelete = async (userId: string) => {
    if (!confirm("Delete this user?")) return;

    try {
      await deleteUser(userId, token);
      showMessage("User deleted");
      await loadUsers();
    } catch {
      showMessage("Delete failed");
    }
  };

  // ===== EDIT =====
  const handleEdit = (user: User) => {
    setEditingUserId(user.id);
    setUsername(user.username);
    setPassword("");
    setRole(user.role);
  };

  return (
    <div className="min-h-screen p-6 bg-[var(--color-background)] text-[var(--color-foreground)]">
      {/* ===== TOAST ===== */}
      {message && (
        <div className="fixed top-5 left-1/2 -translate-x-1/2 bg-black text-white px-4 py-2 rounded animate-fade-in-out">
          {message}
        </div>
      )}

      <div className="max-w-5xl mx-auto space-y-6">
        <h1 className="text-3xl font-bold">Admin Dashboard</h1>

        {/* ===== FORM CARD ===== */}
        <div className="rounded-xl border p-5 shadow-sm bg-white/5 backdrop-blur">
          <h2 className="font-semibold mb-3">
            {editingUserId ? "Update User" : "Create User"}
          </h2>

          <div className="grid md:grid-cols-3 gap-3">
            <input
              className="border rounded px-3 py-2 bg-transparent"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />

            <input
              className="border rounded px-3 py-2 bg-transparent"
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />

            <select
              className="border rounded px-3 py-2 bg-[var(--color-background)] text-[var(--color-foreground)] focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              <option value="user">user</option>
              <option value="admin">admin</option>
              <option value="document_manager">document_manager</option>
            </select>
          </div>

          <div className="mt-4 flex gap-2">
            <button
              onClick={handleSubmit}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded transition"
            >
              {editingUserId ? "Update" : "Create"}
            </button>

            {editingUserId && (
              <button
                onClick={() => {
                  setEditingUserId(null);
                  setUsername("");
                  setPassword("");
                  setRole("user");
                }}
                className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded"
              >
                Cancel
              </button>
            )}
          </div>
        </div>

        {/* ===== TABLE ===== */}
        <div className="rounded-xl border shadow-sm overflow-hidden">
          <div className="p-4 font-semibold border-b">All Users</div>

          {loading ? (
            <p className="p-4">Loading...</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-black/5">
                <tr>
                  <th className="p-3 text-left">Username</th>
                  <th className="p-3 text-left">Role</th>
                  <th className="p-3 text-left">Status</th>
                  <th className="p-3 text-left">Actions</th>
                </tr>
              </thead>

              <tbody>
                {users.map((user) => (
                  <tr
                    key={user.id}
                    className="border-t hover:bg-black/5 transition"
                  >
                    <td className="p-3">{user.username}</td>
                    <td className="p-3">{user.role}</td>
                    <td className="p-3">
                      <span
                        className={`px-2 py-1 rounded text-xs ${
                          user.is_active
                            ? "bg-green-500/20 text-green-600"
                            : "bg-red-500/20 text-red-600"
                        }`}
                      >
                        {user.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="p-3 space-x-2">
                      <button
                        onClick={() => handleEdit(user)}
                        className="px-3 py-1 rounded bg-yellow-400 hover:bg-yellow-500 text-black"
                      >
                        Edit
                      </button>

                      <button
                        onClick={() => handleDelete(user.id)}
                        className="px-3 py-1 rounded bg-red-600 hover:bg-red-700 text-white"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}