"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { authApi, superadminApi, type CreateAdminRequest, type AdminListItem } from "@/lib/api";
import { Shield, ShieldCheck, Plus, Users, Calendar, Mail, User as UserIcon } from "lucide-react";

export default function AdminManagementPage() {
  const router = useRouter();
  const [isSuperadmin, setIsSuperadmin] = useState(false);
  const [admins, setAdmins] = useState<AdminListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [formData, setFormData] = useState<CreateAdminRequest>({
    username: "",
    email: "",
    password: "",
    role: "admin",
  });

  useEffect(() => {
    // Check if user is superadmin
    if (!authApi.isAuthenticated()) {
      router.push('/');
      return;
    }

    if (!authApi.isSuperadmin()) {
      router.push('/main/dashboard');
      return;
    }

    setIsSuperadmin(true);
    loadAdmins();
  }, [router]);

  const loadAdmins = async () => {
    try {
      setIsLoading(true);
      const data = await superadminApi.listAdmins();
      setAdmins(data);
    } catch (err) {
      console.error("Failed to load admins:", err);
      setError("Failed to load admin list");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsCreating(true);
    setError("");
    setSuccess("");

    try {
      const newAdmin = await superadminApi.createAdmin(formData);
      setSuccess(`Admin account "${newAdmin.username}" created successfully!`);
      
      // Reset form
      setFormData({
        username: "",
        email: "",
        password: "",
        role: "admin",
      });
      
      // Reload admin list
      await loadAdmins();
      
      // Hide form after 2 seconds
      setTimeout(() => {
        setShowCreateForm(false);
        setSuccess("");
      }, 2000);
    } catch (err) {
      console.error("Failed to create admin:", err);
      setError(err instanceof Error ? err.message : "Failed to create admin account");
    } finally {
      setIsCreating(false);
    }
  };

  if (!isSuperadmin) {
    return null; // Will redirect in useEffect
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-purple-100 rounded-lg">
              <ShieldCheck className="h-6 w-6 text-purple-600" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Admin Management</h1>
              <p className="text-gray-600 mt-1">Manage admin accounts and permissions</p>
            </div>
          </div>
          <Button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="bg-purple-600 hover:bg-purple-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            Create New Admin
          </Button>
        </div>
      </div>

      {/* Create Admin Form */}
      {showCreateForm && (
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Create New Admin Account</h2>
          
          {error && (
            <div className="mb-4 p-3 rounded-md bg-red-50 border border-red-200">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {success && (
            <div className="mb-4 p-3 rounded-md bg-green-50 border border-green-200">
              <p className="text-sm text-green-600">{success}</p>
            </div>
          )}

          <form onSubmit={handleCreateAdmin} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Username *
                </label>
                <Input
                  type="text"
                  placeholder="johndoe"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  required
                  disabled={isCreating}
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Email *
                </label>
                <Input
                  type="email"
                  placeholder="john@example.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  required
                  disabled={isCreating}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Password *
                </label>
                <Input
                  type="password"
                  placeholder="Strong password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  required
                  disabled={isCreating}
                  minLength={8}
                />
                <p className="text-xs text-gray-500">Minimum 8 characters</p>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Role *
                </label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value as 'admin' | 'superadmin' })}
                  className="w-full h-10 px-3 rounded-md border border-gray-300 bg-white text-sm"
                  disabled={isCreating}
                >
                  <option value="admin">Admin</option>
                  <option value="superadmin">Superadmin</option>
                </select>
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <Button
                type="submit"
                disabled={isCreating}
                className="bg-purple-600 hover:bg-purple-700"
              >
                {isCreating ? "Creating..." : "Create Admin"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setShowCreateForm(false);
                  setError("");
                  setSuccess("");
                }}
                disabled={isCreating}
              >
                Cancel
              </Button>
            </div>
          </form>
        </div>
      )}

      {/* Admin List */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-gray-600" />
            <h2 className="text-lg font-semibold">Admin Accounts</h2>
            <span className="ml-2 px-2 py-1 bg-gray-100 rounded-full text-xs font-medium text-gray-600">
              {admins.length} total
            </span>
          </div>
        </div>

        {isLoading ? (
          <div className="p-8 text-center text-gray-500">
            Loading admin accounts...
          </div>
        ) : admins.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No admin accounts found
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Admin
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Role
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Last Login
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {admins.map((admin) => (
                  <tr key={admin.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-medium">
                          {admin.username.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div className="text-sm font-medium text-gray-900">{admin.username}</div>
                          <div className="text-sm text-gray-500 flex items-center gap-1">
                            <Mail className="h-3 w-3" />
                            {admin.email}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${
                          admin.role === 'superadmin'
                            ? 'bg-purple-100 text-purple-700'
                            : 'bg-blue-100 text-blue-700'
                        }`}
                      >
                        {admin.role === 'superadmin' ? (
                          <ShieldCheck className="h-3 w-3" />
                        ) : (
                          <Shield className="h-3 w-3" />
                        )}
                        {admin.role === 'superadmin' ? 'Super Admin' : 'Admin'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        {new Date(admin.created_at).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {admin.last_login_at ? (
                        <div className="flex items-center gap-1">
                          <UserIcon className="h-3 w-3" />
                          {new Date(admin.last_login_at).toLocaleString()}
                        </div>
                      ) : (
                        <span className="text-gray-400">Never</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
