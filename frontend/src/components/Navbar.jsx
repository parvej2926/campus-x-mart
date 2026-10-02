export function BrandMark({ compact = false }) {
  return (
    <div
      className={
        compact
          ? "flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-sky-400 via-blue-600 to-indigo-700 text-[10px] font-black tracking-[-0.12em] text-white shadow-md ring-2 ring-white/20"
          : "flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-400 via-blue-600 to-indigo-700 text-sm font-black tracking-[-0.14em] text-white shadow-lg ring-4 ring-blue-100"
      }
    >
      cXm
    </div>
  );
}

function Navbar({ setPage, isAuthenticated, onLogout }) {
  return (
    <nav className="bg-blue-600 text-white shadow-sm">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
        <div
          className="flex cursor-pointer items-center gap-3"
          onClick={() => setPage("home")}
        >
          <BrandMark compact />
          <h2 className="text-xl font-bold tracking-tight sm:text-2xl">Campus X Mart</h2>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button className="rounded px-3 py-2 hover:bg-blue-500" onClick={() => setPage("home")}>
            Home
          </button>
          <button className="rounded px-3 py-2 hover:bg-blue-500" onClick={() => setPage("products")}>
            Products
          </button>
          <button className="rounded px-3 py-2 hover:bg-blue-500" onClick={() => setPage("sell")}>
            Sell Item
          </button>
          {isAuthenticated && (
            <>
              <button className="rounded px-3 py-2 hover:bg-blue-500" onClick={() => setPage("chat")}>
                Messages
              </button>
              <button className="rounded px-3 py-2 hover:bg-blue-500" onClick={() => setPage("orders")}>
                Orders
              </button>
              <button className="rounded px-3 py-2 hover:bg-blue-500" onClick={() => setPage("notifications")}>
                Alerts
              </button>
              <button className="rounded px-3 py-2 hover:bg-blue-500" onClick={() => setPage("assistant")}>
                Assistant
              </button>
            </>
          )}
          {isAuthenticated ? (
            <button className="rounded px-3 py-2 hover:bg-blue-500" onClick={onLogout}>
              Logout
            </button>
          ) : (
            <>
              <button className="rounded px-3 py-2 hover:bg-blue-500" onClick={() => setPage("login")}>
                Login
              </button>
              <button className="rounded px-3 py-2 hover:bg-blue-500" onClick={() => setPage("signup")}>
                Sign Up
              </button>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
