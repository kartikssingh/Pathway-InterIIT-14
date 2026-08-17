export default function HelpPage() {
  return (
    <div className="p-8">
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-gray-900">Help & Support</h2>
        <p className="text-sm text-gray-500 mb-4">Get assistance</p>
        <div className="border-t border-gray-200" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="bg-white p-6 rounded-lg border border-gray-200 hover:shadow-md transition-shadow cursor-pointer">
          <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
            <span className="text-2xl">📚</span>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Documentation
          </h3>
          <p className="text-sm text-gray-500">
            Browse our comprehensive guides and API documentation
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200 hover:shadow-md transition-shadow cursor-pointer">
          <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
            <span className="text-2xl">💬</span>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Contact Support
          </h3>
          <p className="text-sm text-gray-500">
            Get in touch with our support team for assistance
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200 hover:shadow-md transition-shadow cursor-pointer">
          <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
            <span className="text-2xl">❓</span>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">FAQ</h3>
          <p className="text-sm text-gray-500">
            Find answers to commonly asked questions
          </p>
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Popular Topics
        </h3>
        <div className="space-y-3">
          <div className="p-3 border-b border-gray-200 last:border-b-0">
            <p className="font-medium text-gray-900">How to create a transaction?</p>
            <p className="text-sm text-gray-500 mt-1">
              Learn how to initiate and manage transactions
            </p>
          </div>
          <div className="p-3 border-b border-gray-200 last:border-b-0">
            {/* <p className="font-medium text-gray-900">Understanding compliance checks</p> */}
            <p className="text-sm text-gray-500 mt-1">
              Overview of KYC, AML, and sanctions screening
            </p>
          </div>
          <div className="p-3 border-b border-gray-200 last:border-b-0">
            <p className="font-medium text-gray-900">Managing user permissions</p>
            <p className="text-sm text-gray-500 mt-1">
              Guide to setting up roles and access control
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
