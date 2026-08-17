export default function SettingsPage() {
  return (
    <div className="p-8">
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-gray-900">Settings</h2>
        <p className="text-sm text-gray-500 mb-4">Manage your preferences</p>
        <div className="border-t border-gray-200" />
      </div>

      <div className="space-y-6">
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Account Settings
          </h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Organization Name
              </label>
              <input
                type="text"
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400"
                placeholder="Vigil 360"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Email
              </label>
              <input
                type="email"
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400"
                placeholder="admin@vigil360.com"
              />
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Notifications
          </h3>
          <div className="space-y-3">
            <label className="flex items-center gap-3">
              <input type="checkbox" className="w-4 h-4" defaultChecked />
              <span className="text-gray-700">Email notifications</span>
            </label>
            <label className="flex items-center gap-3">
              <input type="checkbox" className="w-4 h-4" defaultChecked />
              <span className="text-gray-700">Transaction alerts</span>
            </label>
            <label className="flex items-center gap-3">
              <input type="checkbox" className="w-4 h-4" />
              <span className="text-gray-700">Weekly reports</span>
            </label>
          </div>
        </div>

        <div className="flex justify-end">
          <button className="px-6 py-2 bg-black text-white rounded-md hover:bg-gray-800">
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}
