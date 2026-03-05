"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getAllUsers } from "@/libs/auth/getUser";
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
  const router = useRouter();

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

      // ❌ block creating new admin
      if (!editingUserId && role === "admin") {
        showMessage("Cannot create new admin");
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
    const user = users.find((u) => u.id === userId);

    if (user?.role === "admin") {
      showMessage("Cannot delete admin");
      return;
    }

    if (!confirm("Delete this user?")) return;

    try {
      await deleteUser(userId, token);
      showMessage("User deleted");
      await loadUsers();
    } catch {
      showMessage("Delete failed");
    }
  };

  // ===== EDIT (admin allowed) =====
  const handleEdit = (user: User) => {
    setEditingUserId(user.id);
    setUsername(user.username);
    setPassword("");
    setRole(user.role);
  };

  return (
    <div className="flex min-h-screen flex-col items-center bg-white p-6 text-gray-800">
      
      {/* BACK BUTTON */}
      <div className="w-full max-w-5xl flex justify-end mb-4">
        <button
          onClick={() => router.push("/auth")}
          className="rounded-lg bg-gray-800 px-4 py-2 text-white hover:bg-gray-900"
        >
          ← Back to Sign In
        </button>
      </div>

      {/* TOAST */}
      {message && (
        <div className="fixed top-5 left-1/2 -translate-x-1/2 rounded-lg bg-black px-4 py-2 text-white">
          {message}
        </div>
      )}

      <div className="w-full max-w-5xl space-y-6">

        {/* TITLE */}
        <div className="text-center">
          <h1 className="text-2xl font-bold text-[#1e293b]">
            Admin Dashboard
          </h1>
          <p className="text-gray-500">User Management</p>
        </div>

        {/* FORM */}
        <div className="rounded-2xl border border-gray-100 bg-white p-6 shadow-xl">
          <h2 className="mb-4 font-semibold text-gray-700">
            {editingUserId ? "Update User" : "Create User"}
          </h2>

          <div className="grid md:grid-cols-3 gap-3">

            <input
              className="rounded-lg border border-gray-300 p-3 outline-none focus:border-[#a83b3b] focus:ring-1 focus:ring-[#a83b3b]"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />

            <input
              type="password"
              className="rounded-lg border border-gray-300 p-3 outline-none focus:border-[#a83b3b] focus:ring-1 focus:ring-[#a83b3b]"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />

            <select
              className="rounded-lg border border-gray-300 p-3 bg-white text-gray-800 outline-none focus:border-[#a83b3b] focus:ring-1 focus:ring-[#a83b3b]"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              <option value="user">user</option>
              <option value="document_manager">document_manager</option>
              {editingUserId && role === "admin" && (
                <option value="admin">admin</option>
              )}
            </select>
          </div>

          <div className="mt-4 flex gap-2">
            <button
              onClick={handleSubmit}
              className="rounded-lg bg-[#a83b3b] px-4 py-2 text-white hover:bg-[#8a2f2f]"
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
                className="rounded-lg bg-gray-400 px-4 py-2 text-white hover:bg-gray-500"
              >
                Cancel
              </button>
            )}
          </div>
        </div>

        {/* TABLE */}
        <div className="rounded-2xl border border-gray-100 bg-white shadow-xl overflow-hidden">
          <div className="p-4 font-semibold text-gray-700 border-b">
            All Users
          </div>

          {loading ? (
            <p className="p-4 text-gray-500">Loading...</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-600">
                <tr>
                  <th className="p-3 text-left">Username</th>
                  <th className="p-3 text-left">Role</th>
                  <th className="p-3 text-left">Status</th>
                  <th className="p-3 text-left">Actions</th>
                </tr>
              </thead>

              <tbody>
                {users.map((user) => (
                  <tr key={user.id} className="border-t hover:bg-gray-50">

                    <td className="p-3">{user.username}</td>

                    <td className="p-3">
                      {user.role}
                      {user.role === "admin" && (
                        <span className="ml-2 text-xs text-purple-500">
                          (Protected)
                        </span>
                      )}
                    </td>

                    <td className="p-3">
                      <span
                        className={`px-2 py-1 rounded text-xs ${
                          user.is_active
                            ? "bg-green-100 text-green-600"
                            : "bg-red-100 text-red-600"
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
                        disabled={user.role === "admin"}
                        className={`px-3 py-1 rounded text-white ${
                          user.role === "admin"
                            ? "bg-gray-300 cursor-not-allowed"
                            : "bg-red-600 hover:bg-red-700"
                        }`}
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