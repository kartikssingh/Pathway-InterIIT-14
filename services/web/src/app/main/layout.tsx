"use client";

import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { getInitials } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  LayoutDashboard,
  Users,
  ListOrdered,
  FileText,
  Settings,
  HelpCircle,
  Menu,
  UserPlus,
  LogOut,
  User,
  Shield,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { authApi } from "@/lib/api";

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [username, setUsername] = useState<string | null>(null);
  const [role, setRole] = useState<'admin' | 'superadmin' | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    // Get user info from localStorage
    const storedUsername = authApi.getUsername();
    const storedRole = authApi.getRole();
    
    // If not authenticated, redirect to login
    if (!authApi.isAuthenticated()) {
      router.push('/');
      return;
    }
    
    setUsername(storedUsername);
    setRole(storedRole);
  }, [router]);

  const handleLogout = async () => {
    try {
      await authApi.logout();
      router.push('/');
    } catch (error) {
      console.error('Logout error:', error);
      // Still redirect even if API call fails
      router.push('/');
    }
  };

  const getRoleIcon = () => {
    return role === 'superadmin' ? <ShieldCheck className="h-4 w-4" /> : <Shield className="h-4 w-4" />;
  };

  const getRoleBadgeColor = () => {
    return role === 'superadmin' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700';
  };

  if (!mounted) {
    return null;
  }

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Top Navbar */}
      <header className="flex items-center justify-between px-6 py-4 bg-white">
        <div className="flex items-center gap-2">
          <Menu className="h-5 w-5" />
          <h1 className="text-xl font-bold">Vigil 360</h1>
        </div>
        
        {/* User Profile Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-3 hover:bg-gray-50 rounded-lg p-2 transition-colors">
              <div className="text-right">
                <div className="text-sm font-medium text-gray-900">{username || 'User'}</div>
                <div className={`text-xs font-medium px-2 py-0.5 rounded-full inline-flex items-center gap-1 ${getRoleBadgeColor()}`}>
                  {getRoleIcon()}
                  {role === 'superadmin' ? 'Super Admin' : 'Admin'}
                </div>
              </div>
              <Avatar className="h-10 w-10">
                <AvatarFallback className="bg-gradient-to-br from-blue-500 to-purple-600 text-white">
                  {getInitials(username || '')}
                </AvatarFallback>
              </Avatar>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium">{username}</p>
                <p className="text-xs text-gray-500 capitalize">{role} Account</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link href="/main/settings" className="flex items-center gap-2 cursor-pointer">
                <User className="h-4 w-4" />
                Profile Settings
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem 
              onClick={handleLogout}
              className="text-red-600 focus:text-red-600 focus:bg-red-50 cursor-pointer"
            >
              <LogOut className="h-4 w-4 mr-2" />
              Log Out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </header>

      {/* Horizontal Separator */}
      <div className="border-t border-gray-200" />

      {/* Content Area: Sidebar + Main */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
          <nav className="flex-1 p-6 space-y-1">
            <Link href="/main/dashboard">
              <Button
                variant={pathname === "/main/dashboard" ? "secondary" : "ghost"}
                className={`w-full justify-start gap-3 ${
                  pathname === "/main/dashboard"
                    ? "bg-gray-200 text-gray-900"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                <LayoutDashboard className="h-5 w-5" />
                Dashboard
              </Button>
            </Link>

            <Link href="/main/users">
              <Button
                variant={pathname === "/main/users" ? "secondary" : "ghost"}
                className={`w-full justify-start gap-3 ${
                  pathname === "/main/users"
                    ? "bg-gray-200 text-gray-900"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                <Users className="h-5 w-5" />
                Users
              </Button>
            </Link>

            <Link href="/main/add-user">
              <Button
                variant={pathname === "/main/add-user" ? "secondary" : "ghost"}
                className={`w-full justify-start gap-3 ${
                  pathname === "/main/add-user"
                    ? "bg-gray-200 text-gray-900"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                <UserPlus className="h-5 w-5" />
                Add User
              </Button>
            </Link>

            <Link href="/main/transactions">
              <Button
                variant={pathname === "/main/transactions" ? "secondary" : "ghost"}
                className={`w-full justify-start gap-3 ${
                  pathname === "/main/transactions"
                    ? "bg-gray-200 text-gray-900"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                <ListOrdered className="h-5 w-5" />
                Transactions
              </Button>
            </Link>

            {/* Superadmin Only - Admin Management */}
            {role === 'superadmin' && (
              <>
                <Link href="/main/admin-management">
                  <Button
                    variant={pathname === "/main/admin-management" ? "secondary" : "ghost"}
                    className={`w-full justify-start gap-3 ${
                      pathname === "/main/admin-management"
                        ? "bg-purple-100 text-purple-900"
                        : "text-purple-700 hover:bg-purple-50"
                    }`}
                  >
                    <ShieldCheck className="h-5 w-5" />
                    Admin Management
                  </Button>
                </Link>

                {/* Superadmin Monitoring */}
                <div className="pt-2">
                  <p className="px-3 text-xs font-semibold text-purple-600 uppercase tracking-wider mb-2">
                    System Monitoring
                  </p>
                  <Link href="/main/superadmin">
                    <Button
                      variant={pathname === "/main/superadmin" ? "secondary" : "ghost"}
                      className={`w-full justify-start gap-3 ${
                        pathname === "/main/superadmin"
                          ? "bg-purple-100 text-purple-900"
                          : "text-purple-700 hover:bg-purple-50"
                      }`}
                    >
                      <LayoutDashboard className="h-5 w-5" />
                      Monitoring Dashboard
                    </Button>
                  </Link>
                </div>
              </>
            )}

            {/* Compliance & Sanctions - REMOVED */}
            {/* <Link href="/main/cns">
              <Button
                variant={pathname === "/main/cns" ? "secondary" : "ghost"}
                className={`w-full justify-start gap-3 ${
                  pathname === "/main/cns"
                    ? "bg-gray-200 text-gray-900"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                <FileText className="h-5 w-5" />
                Compliance & Sanctions
              </Button>
            </Link> */}
          </nav>

          <div className="p-6 space-y-1 border-t border-gray-100">
            <Link href="/main/settings">
              <Button
                variant={pathname === "/main/settings" ? "secondary" : "ghost"}
                className={`w-full justify-start gap-3 ${
                  pathname === "/main/settings"
                    ? "bg-gray-200 text-gray-900"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                <Settings className="h-5 w-5" />
                Settings
              </Button>
            </Link>

            <Link href="/main/help">
              <Button
                variant={pathname === "/main/help" ? "secondary" : "ghost"}
                className={`w-full justify-start gap-3 ${
                  pathname === "/main/help"
                    ? "bg-gray-200 text-gray-900"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                <HelpCircle className="h-5 w-5" />
                Help
              </Button>
            </Link>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  );
}