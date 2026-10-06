import { cloneElement, isValidElement, useEffect, useRef, useState } from "react";
import heroImage from "./assets/hero.png";
import { suggestCategory } from "./categorySuggestion.js";
import { mergeCommentList } from "./commentUtils.js";
import { buildLocationQuery, googleMapsEmbedUrl, googleMapsSearchUrl } from "./locationUtils.js";
import { translate, translateNotification } from "./translations.js";
import { youtubeEmbedUrl } from "./youtube.js";
import "./Workspace.css";

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const PRODUCT_PAGE_SIZE = 12;
const blankListing = {
  name: "",
  description: "",
  video_url: "",
  price: "",
  category: "",
  item_condition: "USED_GOOD",
  available_from: "",
  location_id: "",
  status: "AVAILABLE",
};
const protectedPaths = ["/products", "/messages", "/assistant", "/notifications", "/admin/moderation", "/orders", "/listings", "/sell", "/account"];
const navigation = [
  { path: "/", label: "Overview", index: "01" },
  { path: "/products", label: "Products", index: "02" },
  { path: "/messages", label: "Messages", index: "03" },
  { path: "/assistant", label: "Marketplace assistant", index: "04" },
  { path: "/notifications", label: "Notifications", index: "05" },
  { path: "/admin/moderation", label: "Moderation", index: "06" },
  { path: "/orders", label: "Orders", index: "07" },
  { path: "/listings", label: "Your listings", index: "08" },
  { path: "/sell", label: "Sell an item", index: "09" },
  { path: "/account", label: "Account & verification", index: "10" },
];
const mobileNavigation = [
  { path: "/", label: "Home", icon: "⌂" },
  { path: "/products", label: "Products", icon: "▦" },
  { path: "/messages", label: "Messages", icon: "✉" },
  { path: "/notifications", label: "Alerts", icon: "!" },
];
const localizableProps = new Set(["aria-label", "aria-description", "detail", "kicker", "label", "placeholder", "title"]);

function Localized({ language, children }) {
  function visit(node) {
    if (typeof node === "string") return translate(node, language);
    if (typeof node === "number" && language === "bn") return new Intl.NumberFormat("bn-BD").format(node);
    if (Array.isArray(node)) return node.map(visit);
    if (!isValidElement(node)) return node;
    if (node.props["data-no-translate"]) return node;

    const props = {};
    for (const [key, value] of Object.entries(node.props)) {
      if (key === "children") {
        props.children = visit(value);
      } else if (localizableProps.has(key) && typeof value === "string") {
        props[key] = translate(value, language);
      }
    }
    return cloneElement(node, props);
  }

  return visit(children);
}

async function api(path, method = "GET", body) {
  const token = localStorage.getItem("access_token");
  const response = await fetch(`${API}${path}`, {
    method,
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  if (response.status === 204) return {};
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || "The request could not be completed.");
  return payload;
}

function moveTo(path, setPath) {
  if (window.location.pathname !== path) window.history.pushState({}, "", path);
  setPath(path);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

const languageOptions = [
  { code: "en", label: "EN" },
  { code: "bn", label: "বাংলা" },
];

function LanguageSwitcher({ value, onChange }) {
  return (
    <div className="language-switcher" role="group" aria-label={translate("Choose language", value)}>
      {languageOptions.map((option) => (
        <button
          key={option.code}
          type="button"
          className={`language-option${value === option.code ? " language-option-active" : ""}`}
          onClick={() => onChange(option.code)}
          aria-pressed={value === option.code}
          aria-label={option.code === "en" ? translate("English", value) : translate("Bangla", value)}
          lang={option.code}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function Brand({ light = false }) {
  return (
    <span className={`brand-lockup${light ? " brand-light" : ""}`}>
      <span className="brand-stamp" aria-hidden="true">cXm</span>
      <span>campus <strong>x</strong> mart</span>
    </span>
  );
}

function Field({ label, id, multiline = false, ...props }) {
  return (
    <label className="field" htmlFor={id}>
      <span>{label}</span>
      {multiline ? (
        <textarea id={id} {...props} />
      ) : (
        <input id={id} {...props} />
      )}
    </label>
  );
}

function money(value, language = "en") {
  const locale = language === "bn" ? "bn-BD" : "en-BD";
  return `৳${new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(Number(value) || 0)}`;
}

function hasVerifiedContact(user) {
  return Boolean(user?.email_verified || user?.phone_verified);
}

function localDateInputValue(value = new Date()) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function PageHeading({ kicker, title, detail, action }) {
  return (
    <div className="page-heading">
      <div>
        <p className="eyebrow">{kicker}</p>
        <h1>{title}</h1>
        {detail && <p className="page-detail">{detail}</p>}
      </div>
      {action}
    </div>
  );
}

function RatingStars({ rating, onChange, label = "Product rating", language = "en" }) {
  const filledRating = Math.round(Number(rating) || 0);
  if (!onChange) {
    return <span className="rating-stars" role="img" aria-label={rating ? `${rating} ${translate("out of 5 stars", language)}` : translate("No rating", language)}>
      {[1, 2, 3, 4, 5].map((star) => <span key={star} className={star <= filledRating ? "rating-star rating-star-filled" : "rating-star"}>★</span>)}
    </span>;
  }
  return <span className="rating-picker" role="group" aria-label={label}>
    {[1, 2, 3, 4, 5].map((star) => <button type="button" key={star} className={star <= filledRating ? "rating-star rating-star-filled" : "rating-star"} aria-label={`${new Intl.NumberFormat(language === "bn" ? "bn-BD" : "en-BD").format(star)} ${translate(star === 1 ? "star" : "stars", language)}`} aria-pressed={Number(rating) === star} onClick={() => onChange(star)}>★</button>)}
  </span>;
}

function ModerationCard({ report, onSetStatus, language }) {
  return (
    <Localized language={language}><article className="moderation-report">
      <div className="moderation-report-main">
        <div className="moderation-report-heading"><span className={`order-state order-state-${report.status.toLowerCase()}`}>{report.status.toLowerCase()}</span><span className="order-reference">REPORT #{String(report.report_id).padStart(5, "0")}</span><time>{new Date(report.created_at).toLocaleString(language === "bn" ? "bn-BD" : "en-BD")}</time></div>
        <h2 data-no-translate>{report.item?.name || "Removed product"}</h2>
        <p data-no-translate>{report.reason}</p>
        <div className="moderation-parties"><span>Reported by <strong data-no-translate>{report.reporter.full_name}</strong></span>{report.reported_user && <span>Seller <strong data-no-translate>{report.reported_user.full_name}</strong></span>}{report.reviewer_username && <span>Reviewed by <strong data-no-translate>@{report.reviewer_username}</strong></span>}</div>
      </div>
      <div className="moderation-actions">{report.status === "OPEN" && <button className="button button-outline" onClick={() => onSetStatus(report.report_id, "REVIEWING")}>Start review</button>}{["OPEN", "REVIEWING"].includes(report.status) && <><button className="button button-dark" onClick={() => onSetStatus(report.report_id, "RESOLVED")}>Resolve</button><button className="button button-text-danger" onClick={() => onSetStatus(report.report_id, "REJECTED")}>Reject</button></>}</div>
    </article></Localized>
  );
}

function Landing({ onNavigate, language, onLanguageChange }) {
  return (
    <Localized language={language}><main className="welcome-page">
      <header className="welcome-nav">
        <Brand />
        <div className="welcome-actions">
          <LanguageSwitcher value={language} onChange={onLanguageChange} />
          <button className="button button-quiet" onClick={() => onNavigate("/login")}>Log in</button>
          <button className="button button-dark" onClick={() => onNavigate("/register")}>Join the marketplace <span aria-hidden="true">↗</span></button>
        </div>
      </header>
      <section className="welcome-hero">
        <img className="welcome-image" src={heroImage} alt="" />
        <div className="welcome-shade" />
        <div className="welcome-copy">
          <p className="eyebrow eyebrow-light">MADE FOR CAMPUS LIFE</p>
          <h1>Good things<br />find a second home.</h1>
          <p>Buy and sell the things that make student life a little easier, right here on campus.</p>
          <button className="button button-lime" onClick={() => onNavigate("/register")}>Start selling <span aria-hidden="true">↗</span></button>
        </div>
        <div className="hero-caption"><span>01 / YOUR CAMPUS, YOUR MARKET</span><span>Pass it on. Keep it local.</span></div>
      </section>
      <section className="welcome-foot" aria-label="Marketplace values">
        <div><span className="foot-number">01</span><strong>List what you no longer need</strong><span>Make room for what comes next.</span></div>
        <div><span className="foot-number">02</span><strong>Find useful things nearby</strong><span>Keep good stuff in circulation.</span></div>
        <div><span className="foot-number">03</span><strong>Meet on your campus</strong><span>Simple exchanges, close to home.</span></div>
      </section>
      <section className="welcome-admin" aria-label="Administrator sign in">
        <div><span className="welcome-admin-label">ADMINISTRATOR ACCESS</span><p>Manage reports and keep the marketplace safe.</p></div>
        <button className="button button-outline" onClick={() => onNavigate("/admin/login")}>Admin sign in <span aria-hidden="true">↗</span></button>
      </section>
    </main></Localized>
  );
}

function AuthPage({ register, adminLogin = false, onNavigate, onSubmit, busy, notice, language, onLanguageChange }) {
  const [username, setUsername] = useState("");
  const [usernameCheck, setUsernameCheck] = useState({ value: "", available: null, message: "" });
  const normalizedUsername = username.trim().toLowerCase();
  const hasCurrentUsernameCheck = usernameCheck.value === normalizedUsername;

  useEffect(() => {
    if (!register || normalizedUsername.length < 3) return undefined;
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch(`${API}/api/auth/check-username?username=${encodeURIComponent(normalizedUsername)}`, { signal: controller.signal });
        const result = await response.json();
        setUsernameCheck({ value: normalizedUsername, available: Boolean(result.available), message: result.message });
      } catch (error) {
        if (error.name !== "AbortError") {
          setUsernameCheck({ value: normalizedUsername, available: null, message: "Could not check now; the server will validate when you register." });
        }
      }
    }, 300);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [register, normalizedUsername]);

  const usernameChecking = register && normalizedUsername.length >= 3 && !hasCurrentUsernameCheck;
  const usernameTaken = hasCurrentUsernameCheck && usernameCheck.available === false;
  const canSubmit = !busy && (!register || (normalizedUsername.length >= 3 && !usernameChecking && !usernameTaken));

  return (
    <Localized language={language}><main className="auth-page">
      <section className="auth-art">
        <img src={heroImage} alt="" />
        <div className="auth-art-shade" />
        <button className="brand-home" onClick={() => onNavigate("/")}><Brand light /></button>
        <div className="auth-art-copy"><p className="eyebrow eyebrow-light">YOUR CAMPUS MARKETPLACE</p><h1>Pass it on.<br />Find your next.</h1><p>Good things are already moving around campus.</p></div>
      </section>
      <section className="auth-panel">
        <div className="auth-form-wrap">
          <div className="auth-language-switcher"><LanguageSwitcher value={language} onChange={onLanguageChange} /></div>
          <button className="back-link" onClick={() => onNavigate("/")}>← Back to home</button>
          <p className="eyebrow">{register ? "NEW TO CAMPUS X MART" : adminLogin ? "ADMINISTRATOR ACCESS" : "WELCOME BACK"}</p>
          <h2>{register ? "Create your account" : adminLogin ? "Admin sign in" : "Sign in to continue"}</h2>
          <p className="auth-intro">{register ? "A few details, then you’re ready to list." : adminLogin ? "Sign in with your administrator account." : "Pick up where your campus marketplace left off."}</p>
          <form className="form-stack" onSubmit={onSubmit}>
            {register && <>
              <Field id="full_name" label="Full name" name="full_name" autoComplete="name" required minLength={2} />
              <div className="username-field"><Field id="username" label="Username" name="username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required minLength={3} aria-describedby="username-availability" /><span id="username-availability" className={`username-availability${usernameTaken ? " username-unavailable" : hasCurrentUsernameCheck && usernameCheck.available ? " username-available" : ""}`} aria-live="polite">{normalizedUsername.length < 3 ? "At least 3 characters" : usernameChecking ? "Checking availability…" : usernameCheck.message}</span></div>
              <Field id="phone" label="Phone number" name="phone" type="tel" autoComplete="tel" />
            </>}
            <Field id="email" label="Campus email" name="email" type="email" autoComplete="email" required />
            <Field id="password" label="Password" name="password" type="password" autoComplete={register ? "new-password" : "current-password"} minLength={8} required />
            {notice && <p className="notice notice-error" role="alert">{notice}</p>}
            <button className="button button-dark button-wide" disabled={!canSubmit}>{busy ? "Please wait…" : register ? "Create account" : "Sign in"}<span aria-hidden="true">↗</span></button>
          </form>
          {adminLogin ? <p className="auth-switch">Administrator accounts only.</p> : <p className="auth-switch">{register ? "Already have an account?" : "New to the marketplace?"} <button onClick={() => onNavigate(register ? "/login" : "/register")}>{register ? "Log in" : "Create an account"}</button></p>}
        </div>
      </section>
    </main></Localized>
  );
}

function ListingRow({ item, onEdit, onDelete, onUpload, language }) {
  return (
    <Localized language={language}><article className="listing-row">
      {item.media_url ? <img className="listing-thumb" src={item.media_url} alt="" /> : <div className="listing-thumb listing-thumb-empty" aria-hidden="true"><span>{item.category?.slice(0, 1) || "X"}</span></div>}
      <div className="listing-main">
        <div className="listing-title-line"><h3 data-no-translate>{item.name}</h3><span className={`status-pill status-${String(item.status).toLowerCase()}`}>{item.status}</span></div>
        <p><span data-no-translate>{item.category}</span> <span aria-hidden="true">·</span> {translate(String(item.item_condition || "").replaceAll("_", " ").toLowerCase().replace("used_", "used "), language)}</p>
        <strong className="listing-price">{money(item.price, language)}</strong>
      </div>
      <div className="listing-actions">
        <button className="button button-outline" onClick={() => onEdit(item)}>Edit</button>
        <button className="button button-text-danger" onClick={() => onDelete(item.item_id)}>Delete</button>
        <label className="upload-link">Add photo<input type="file" accept="image/*,.pdf,.txt,.zip" onChange={(event) => onUpload(item.item_id, event.target.files?.[0])} /></label>
      </div>
    </article></Localized>
  );
}

export default function WorkspaceApp() {
  const [path, setPath] = useState(window.location.pathname);
  const [language, setLanguage] = useState(() => localStorage.getItem("campus_x_mart_language") === "bn" ? "bn" : "en");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [user, setUser] = useState(null);
  const [authReady, setAuthReady] = useState(() => !localStorage.getItem("access_token"));
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [items, setItems] = useState([]);
  const [locations, setLocations] = useState([]);
  const [locationFormOpen, setLocationFormOpen] = useState(false);
  const [locationBusy, setLocationBusy] = useState(false);
  const [locationDraft, setLocationDraft] = useState({ location_name: "", campus_name: "", address: "", latitude: "", longitude: "" });
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [productSearch, setProductSearch] = useState("");
  const [productCategory, setProductCategory] = useState("");
  const [productCondition, setProductCondition] = useState("");
  const [productMinPrice, setProductMinPrice] = useState("");
  const [productMaxPrice, setProductMaxPrice] = useState("");
  const [productSort, setProductSort] = useState("newest");
  const [productPage, setProductPage] = useState(1);
  const [productTotal, setProductTotal] = useState(0);
  const [openComments, setOpenComments] = useState(null);
  const [commentsByItem, setCommentsByItem] = useState({});
  const [commentDrafts, setCommentDrafts] = useState({});
  const [openReviews, setOpenReviews] = useState(null);
  const [reviewsByItem, setReviewsByItem] = useState({});
  const [reviewingOrder, setReviewingOrder] = useState(null);
  const [ratingDrafts, setRatingDrafts] = useState({});
  const [reviewDrafts, setReviewDrafts] = useState({});
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [selectedPeer, setSelectedPeer] = useState(null);
  const [userSearch, setUserSearch] = useState("");
  const [userSearchResults, setUserSearchResults] = useState([]);
  const [searchingUsers, setSearchingUsers] = useState(false);
  const [messages, setMessages] = useState([]);
  const [messageDraft, setMessageDraft] = useState("");
  const [orders, setOrders] = useState([]);
  const [orderStatus, setOrderStatus] = useState("ALL");
  const [meetupDrafts, setMeetupDrafts] = useState({});
  const [notifications, setNotifications] = useState([]);
  const [unreadNotifications, setUnreadNotifications] = useState(0);
  const [notificationFilter, setNotificationFilter] = useState("ALL");
  const [reports, setReports] = useState([]);
  const [reportStatusFilter, setReportStatusFilter] = useState("OPEN");
  const [moderationTab, setModerationTab] = useState("REPORTS");
  const [adminUserSearch, setAdminUserSearch] = useState("");
  const [adminUsers, setAdminUsers] = useState([]);
  const [adminUsersLoading, setAdminUsersLoading] = useState(false);
  const [adminBanReason, setAdminBanReason] = useState("");
  const [reportingItem, setReportingItem] = useState(null);
  const [reportReason, setReportReason] = useState("");
  const [assistantMessages, setAssistantMessages] = useState([{ id: "welcome", role: "assistant", content: "Hi! I can help you list an item, understand an order, or find your way around Campus X Mart." }]);
  const [assistantDraft, setAssistantDraft] = useState("");
  const [assistantBusy, setAssistantBusy] = useState(false);
  const [listing, setListing] = useState(blankListing);
  const [editingId, setEditingId] = useState(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [channel, setChannel] = useState("EMAIL");
  const [code, setCode] = useState("");
  const [resendIn, setResendIn] = useState(0);
  const notificationIds = useRef(new Set());
  const selectedConversationRef = useRef(null);
  const assistantScrollRef = useRef(null);
  const route = user
    ? path === "/login" || path === "/register"
      ? "/"
      : path === "/admin/login"
        ? user.admin_session ? "/admin/moderation" : "/"
        : path === "/admin/moderation" && !user.admin_session
          ? "/"
        : path
    : protectedPaths.includes(path) ? "/login" : path;

  useEffect(() => {
    selectedConversationRef.current = selectedConversation;
  }, [selectedConversation]);

  useEffect(() => {
    const onPopState = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [route]);

  useEffect(() => {
    document.documentElement.lang = language;
    try {
      localStorage.setItem("campus_x_mart_language", language);
    } catch {
      setNotice(translate("Your language preference could not be saved on this device.", language));
    }
  }, [language]);

  useEffect(() => {
    if (!mobileMenuOpen) return undefined;
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKeyDown = (event) => {
      if (event.key === "Escape") setMobileMenuOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = originalOverflow;
    };
  }, [mobileMenuOpen]);

  useEffect(() => {
    if (!localStorage.getItem("access_token")) return;
    api("/api/auth/me")
      .then((result) => setUser(result.user))
      .catch(() => localStorage.removeItem("access_token"))
      .finally(() => setAuthReady(true));
  }, []);

  useEffect(() => {
    if (!user) return;
    api("/api/listings/mine")
      .then((result) => setItems(result.items || []))
      .catch((error) => setNotice(error.message));
  }, [user]);

  useEffect(() => {
    if (!user) return;
    api("/api/locations")
      .then((result) => setLocations(result.locations || []))
      .catch((error) => setNotice(error.message));
  }, [user]);

  useEffect(() => {
    if (!user || route !== "/products") return undefined;
    let active = true;
    const params = new URLSearchParams();
    if (productSearch.trim()) params.set("q", productSearch.trim());
    if (productCategory) params.set("category", productCategory);
    if (productCondition) params.set("condition", productCondition);
    if (productMinPrice) params.set("min_price", productMinPrice);
    if (productMaxPrice) params.set("max_price", productMaxPrice);
    params.set("sort", productSort);
    params.set("limit", String(PRODUCT_PAGE_SIZE));
    params.set("offset", String((productPage - 1) * PRODUCT_PAGE_SIZE));
    api(`/api/items${params.size ? `?${params}` : ""}`)
      .then((result) => {
        if (!active) return;
        setProducts(result.items || []);
        setCategories(result.categories || []);
        setProductTotal(result.total_count || 0);
      })
      .catch((error) => {
        if (active) setNotice(error.message);
      });
    return () => { active = false; };
  }, [user, route, productSearch, productCategory, productCondition, productMinPrice, productMaxPrice, productSort, productPage]);

  useEffect(() => {
    if (!user || route !== "/messages") return undefined;
    let active = true;
    const loadConversations = () => api("/api/messages/conversations")
      .then((result) => {
        if (!active) return;
        const nextConversations = result.conversations || [];
        setConversations(nextConversations);
        setSelectedConversation((current) => current || nextConversations[0]?.user_id || null);
      })
      .catch((error) => {
        if (active) setNotice(error.message);
      });
    loadConversations();
    const timer = window.setInterval(loadConversations, 30000);
    return () => { active = false; window.clearInterval(timer); };
  }, [user, route]);

  useEffect(() => {
    if (!user || route !== "/messages") return undefined;
    const query = userSearch.trim();
    if (query.length < 2) {
      setUserSearchResults([]);
      setSearchingUsers(false);
      return undefined;
    }

    let active = true;
    const timer = window.setTimeout(() => {
      setSearchingUsers(true);
      api(`/api/users/search?q=${encodeURIComponent(query)}`)
        .then((result) => {
          if (active) setUserSearchResults(result.users || []);
        })
        .catch((error) => {
          if (active) setNotice(error.message);
        })
        .finally(() => {
          if (active) setSearchingUsers(false);
        });
    }, 250);

    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [user, route, userSearch]);

  useEffect(() => {
    if (!user || route !== "/messages" || !selectedConversation) return undefined;
    let active = true;
    const loadMessages = () => api(`/api/messages/${selectedConversation}`)
      .then((result) => {
        if (active) setMessages(result.messages || []);
      })
      .catch((error) => {
        if (active) setNotice(error.message);
      });
    api(`/api/messages/${selectedConversation}/read`, "POST").catch(() => {});
    loadMessages();
    const timer = window.setInterval(loadMessages, 30000);
    return () => { active = false; window.clearInterval(timer); };
  }, [user, route, selectedConversation]);

  useEffect(() => {
    if (!user || route !== "/orders") return undefined;
    let active = true;
    api("/api/orders")
      .then((result) => {
        if (active) setOrders(result.orders || []);
      })
      .catch((error) => {
        if (active) setNotice(error.message);
      });
    return () => { active = false; };
  }, [user, route]);

  useEffect(() => {
    if (!user || !user.admin_session || route !== "/admin/moderation") return undefined;
    let active = true;
    const query = reportStatusFilter === "ALL" ? "" : `?status=${reportStatusFilter}`;
    api(`/api/admin/reports${query}`)
      .then((result) => { if (active) setReports(result.reports || []); })
      .catch((error) => { if (active) setNotice(error.message); });
    return () => { active = false; };
  }, [user, route, reportStatusFilter]);

  useEffect(() => {
    if (!user || !user.admin_session || route !== "/admin/moderation" || moderationTab !== "USERS") return undefined;
    const query = adminUserSearch.trim();
    if (query.length < 2) {
      setAdminUsers([]);
      setAdminUsersLoading(false);
      return undefined;
    }

    let active = true;
    const timer = window.setTimeout(() => {
      setAdminUsersLoading(true);
      api(`/api/admin/users/search?q=${encodeURIComponent(query)}`)
        .then((result) => {
          if (active) setAdminUsers(result.users || []);
        })
        .catch((error) => {
          if (active) setNotice(error.message);
        })
        .finally(() => {
          if (active) setAdminUsersLoading(false);
        });
    }, 250);

    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [user, route, moderationTab, adminUserSearch]);

  useEffect(() => {
    if (!user) return undefined;
    let active = true;
    let socket;
    let reconnectTimer;
    let reconnectDelay = 1000;

    const connect = async () => {
      try {
        const ticketResult = await api("/api/ws/ticket", "POST");
        if (!active) return;
        const apiUrl = new URL(API);
        const protocol = apiUrl.protocol === "https:" ? "wss:" : "ws:";
        const socketUrl = `${protocol}//${apiUrl.host}/api/ws/notifications?ticket=${encodeURIComponent(ticketResult.ticket)}`;
        const nextSocket = new WebSocket(socketUrl);
        socket = nextSocket;
        nextSocket.onopen = () => { reconnectDelay = 1000; };
        nextSocket.onmessage = (event) => {
          const payload = JSON.parse(event.data);
          if (payload.type !== "notification" || notificationIds.current.has(payload.notification.notification_id)) return;
          notificationIds.current.add(payload.notification.notification_id);
          setNotifications((current) => [payload.notification, ...current].slice(0, 100));
          if (!payload.notification.is_read) setUnreadNotifications((count) => count + 1);
          if (payload.notification.notification_type === "MESSAGE") {
            api("/api/messages/conversations")
              .then((result) => setConversations(result.conversations || []))
              .catch((error) => setNotice(error.message));
            const peerId = selectedConversationRef.current;
            if (peerId) {
              api(`/api/messages/${peerId}`)
                .then((result) => setMessages(result.messages || []))
                .then(() => api(`/api/messages/${peerId}/read`, "POST"))
                .catch((error) => setNotice(error.message));
            }
          }
          if (payload.notification.notification_type === "ORDER") {
            api("/api/orders")
              .then((result) => setOrders(result.orders || []))
              .catch((error) => setNotice(error.message));
          }
        };
        nextSocket.onclose = () => {
          if (!active || socket !== nextSocket) return;
          reconnectTimer = window.setTimeout(connect, reconnectDelay);
          reconnectDelay = Math.min(reconnectDelay * 2, 30000);
        };
      } catch {
        if (!active) return;
        reconnectTimer = window.setTimeout(connect, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, 30000);
      }
    };

    api("/api/notifications?limit=100")
      .then((result) => {
        if (!active) return;
        setNotifications(result.notifications || []);
        notificationIds.current = new Set((result.notifications || []).map((notification) => notification.notification_id));
        setUnreadNotifications(result.unread_count || 0);
      })
      .catch((error) => setNotice(error.message))
      .finally(() => { if (active) connect(); });

    return () => {
      active = false;
      window.clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [user]);

  useEffect(() => {
    if (!user || route !== "/messages") return undefined;
    let active = true;
    let socket;
    let reconnectTimer;
    let reconnectDelay = 1000;

    const connect = async () => {
      try {
        const ticketResult = await api("/api/ws/ticket", "POST");
        if (!active) return;
        const apiUrl = new URL(API);
        const protocol = apiUrl.protocol === "https:" ? "wss:" : "ws:";
        const socketUrl = `${protocol}//${apiUrl.host}/api/ws/chat?ticket=${encodeURIComponent(ticketResult.ticket)}`;
        socket = new WebSocket(socketUrl);

        socket.onmessage = (event) => {
          const payload = JSON.parse(event.data);
          if (payload.type !== "message" || !payload.message) return;

          const message = payload.message;
          setMessages((current) => current.some((item) => item.message_id === message.message_id) ? current : [...current, message]);
          setConversations((current) => {
            const peerId = message.sender_id === user.id ? message.receiver_id : message.sender_id;
            const peer = current.find((item) => item.user_id === peerId);
            return [{ ...(peer || { user_id: peerId, username: "", full_name: "" }), last_message: message.message_text, last_message_at: message.sent_at }, ...current.filter((item) => item.user_id !== peerId)];
          });
          if (message.sender_id !== user.id && selectedConversationRef.current === message.sender_id) {
            api(`/api/messages/${message.sender_id}/read`, "POST").catch(() => {});
          }
        };

        socket.onclose = () => {
          if (!active) return;
          reconnectTimer = window.setTimeout(connect, reconnectDelay);
          reconnectDelay = Math.min(reconnectDelay * 2, 30000);
        };
      } catch {
        if (!active) return;
        reconnectTimer = window.setTimeout(connect, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, 30000);
      }
    };

    connect();

    return () => {
      active = false;
      window.clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [user, route]);

  useEffect(() => {
    if (!resendIn) return undefined;
    const timer = window.setInterval(() => setResendIn((value) => Math.max(value - 1, 0)), 1000);
    return () => window.clearInterval(timer);
  }, [resendIn]);

  useEffect(() => {
    assistantScrollRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [assistantMessages]);

  function navigate(nextPath) {
    setMobileMenuOpen(false);
    setNotice("");
    moveTo(nextPath, setPath);
  }

  async function handleAuth(event) {
    event.preventDefault();
    setNotice("");
    setBusy(true);
    const values = Object.fromEntries(new FormData(event.currentTarget).entries());
    try {
      const isRegister = path === "/register";
      const isAdminLogin = path === "/admin/login";
      const authPath = isRegister ? "/api/auth/register" : isAdminLogin ? "/api/admin/login" : "/api/auth/login";
      const result = await api(authPath, "POST", values);
      if (isAdminLogin && (result.user.role !== "ADMIN" || result.user.admin_session !== true)) {
        throw new Error("This account does not have administrator access.");
      }
      localStorage.setItem("access_token", result.access_token);
      setUser(result.user);
      navigate(isAdminLogin ? "/admin/moderation" : "/");
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  function updateListing(event) {
    const { name, value } = event.target;
    setListing((current) => ({ ...current, [name]: value }));
  }

  async function saveListing(event) {
    event.preventDefault();
    if (!hasVerifiedContact(user)) {
      navigate("/account");
      setNotice("Verify your email or phone number before posting a listing.");
      return;
    }
    setNotice("");
    setBusy(true);
    try {
      const result = await api(editingId ? `/api/listings/${editingId}` : "/api/listings", editingId ? "PUT" : "POST", {
        ...listing,
        price: Number(listing.price),
        location_id: listing.location_id ? Number(listing.location_id) : null,
      });
      setItems((current) => editingId ? current.map((item) => item.item_id === editingId ? result.item : item) : [result.item, ...current]);
      setListing(blankListing);
      setEditingId(null);
      setNotice(editingId ? "Your listing has been updated." : "Your listing is live.");
      navigate("/listings");
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  function startEditing(item) {
    setListing({
      name: item.name,
      description: item.description,
      video_url: item.video_url || "",
      price: String(item.price),
      category: item.category,
      item_condition: item.item_condition,
      available_from: item.available_from || "",
      location_id: item.location_id ? String(item.location_id) : "",
      status: item.status || "AVAILABLE",
    });
    setEditingId(item.item_id);
    navigate("/sell");
  }

  async function createLocation() {
    if (!locationDraft.location_name.trim()) {
      setNotice("Enter a location name first.");
      return;
    }
    setLocationBusy(true);
    const coordinate = (value) => value === "" ? null : Number(value);
    try {
      const result = await api("/api/locations", "POST", {
        ...locationDraft,
        latitude: coordinate(locationDraft.latitude),
        longitude: coordinate(locationDraft.longitude),
      });
      const location = result.location;
      setLocations((current) => [...current, location].sort((left, right) => `${left.campus_name || ""}${left.location_name}`.localeCompare(`${right.campus_name || ""}${right.location_name}`)));
      setListing((current) => ({ ...current, location_id: String(location.location_id) }));
      setLocationDraft({ location_name: "", campus_name: "", address: "", latitude: "", longitude: "" });
      setLocationFormOpen(false);
      setNotice("Campus location added.");
    } catch (error) {
      setNotice(error.message);
    } finally {
      setLocationBusy(false);
    }
  }

  async function deleteListing(itemId) {
    if (!window.confirm("Delete this listing? This cannot be undone.")) return;
    try {
      await api(`/api/listings/${itemId}`, "DELETE");
      setItems((current) => current.filter((item) => item.item_id !== itemId));
      setNotice("Listing deleted.");
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function toggleProductReaction(product, reactionType) {
    try {
      const isActive = product.current_reaction === reactionType;
      const result = await api(`/api/items/${product.item_id}/reaction`, isActive ? "DELETE" : "PUT", isActive ? undefined : { reaction_type: reactionType });
      setProducts((current) => current.map((item) => item.item_id === product.item_id ? { ...item, ...result } : item));
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function refreshComments(itemId) {
    try {
      const result = await api(`/api/items/${itemId}/comments`);
      setCommentsByItem((current) => ({ ...current, [itemId]: mergeCommentList(current[itemId] || [], result.comments || []) }));
      return result.comments || [];
    } catch (error) {
      setNotice(error.message);
      return [];
    }
  }

  useEffect(() => {
    if (!openComments) return undefined;
    refreshComments(openComments);
    const timer = window.setInterval(() => {
      refreshComments(openComments);
    }, 4000);
    return () => window.clearInterval(timer);
  }, [openComments]);

  async function toggleProductComments(itemId) {
    if (openComments === itemId) {
      setOpenComments(null);
      return;
    }
    setOpenComments(itemId);
    if (commentsByItem[itemId]) return;
    await refreshComments(itemId);
  }

  async function submitProductComment(event, itemId) {
    event.preventDefault();
    const commentText = commentDrafts[itemId]?.trim();
    if (!commentText) return;
    try {
      const result = await api(`/api/items/${itemId}/comments`, "POST", { comment_text: commentText });
      setCommentsByItem((current) => ({ ...current, [itemId]: mergeCommentList(current[itemId] || [], [result.comment]) }));
      setCommentDrafts((current) => ({ ...current, [itemId]: "" }));
      setProducts((current) => current.map((item) => item.item_id === itemId ? { ...item, comment_count: item.comment_count + 1 } : item));
      await refreshComments(itemId);
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function submitProductReport(event, itemId) {
    event.preventDefault();
    const reason = reportReason.trim();
    if (!reason) return;
    try {
      await api(`/api/items/${itemId}/reports`, "POST", { reason });
      setReportingItem(null);
      setReportReason("");
      setNotice("Report sent to the moderation team.");
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function setModerationStatus(reportId, nextStatus) {
    try {
      const result = await api(`/api/admin/reports/${reportId}`, "PATCH", { status: nextStatus });
      setReports((current) => current.map((report) => report.report_id === reportId ? result.report : report));
      setNotice(`Report ${nextStatus.toLowerCase()}.`);
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function updatePostingBan(target) {
    const banned = !target.posting_banned;
    try {
      const result = await api(`/api/admin/users/${target.user_id}/posting-ban`, "PATCH", {
        banned,
        reason: banned ? adminBanReason.trim() : null,
      });
      setAdminUsers((current) => current.map((person) => person.user_id === target.user_id ? result.user : person));
      if (banned) setAdminBanReason("");
      setNotice(banned ? `${target.full_name} is now banned from posting.` : `${target.full_name} can post again.`);
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function loadItemReviews(itemId) {
    const result = await api(`/api/items/${itemId}/reviews`);
    setReviewsByItem((current) => ({ ...current, [itemId]: result }));
    return result;
  }

  async function toggleProductReviews(itemId) {
    if (openReviews === itemId) {
      setOpenReviews(null);
      return;
    }
    setOpenReviews(itemId);
    if (reviewsByItem[itemId]) return;
    try {
      await loadItemReviews(itemId);
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function startOrderReview(order) {
    try {
      const result = await loadItemReviews(order.item_id);
      setRatingDrafts((current) => ({ ...current, [order.item_id]: result.my_review?.rating || 5 }));
      setReviewDrafts((current) => ({ ...current, [order.item_id]: result.my_review?.review_text || "" }));
      setReviewingOrder(order.order_id);
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function submitOrderReview(event, order) {
    event.preventDefault();
    try {
      await api(`/api/items/${order.item_id}/reviews`, "PUT", {
        rating: ratingDrafts[order.item_id] || 5,
        review_text: reviewDrafts[order.item_id] || null,
      });
      await loadItemReviews(order.item_id);
      setReviewingOrder(null);
      setNotice("Your review has been saved.");
    } catch (error) {
      setNotice(error.message);
    }
  }

  function openConversationWith(peer) {
    setSelectedConversation(peer.user_id);
    setSelectedPeer(peer);
    setMessages([]);
    navigate("/messages");
  }

  async function sendMessage(event) {
    event.preventDefault();
    const text = messageDraft.trim();
    if (!text || !selectedConversation) return;
    try {
      const result = await api(`/api/messages/${selectedConversation}`, "POST", { message_text: text });
      setMessages((current) => [...current, result.message]);
      setMessageDraft("");
      setConversations((current) => {
        const peer = current.find((item) => item.user_id === selectedConversation) || selectedPeer;
        if (!peer) return current;
        const next = [{ ...peer, last_message: text, last_message_at: result.message.sent_at }, ...current.filter((item) => item.user_id !== selectedConversation)];
        return next;
      });
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function hideMessage(messageId) {
    if (!selectedConversation) return;
    try {
      await api(`/api/messages/${selectedConversation}/${messageId}`, "DELETE");
      setMessages((current) => current.filter((message) => message.message_id !== messageId));
      const result = await api("/api/messages/conversations");
      setConversations(result.conversations || []);
      setNotice("Message deleted from your view.");
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function requestProductOrder(product) {
    if (!hasVerifiedContact(user)) {
      navigate("/account");
      setNotice("Verify your email or phone number before requesting to buy.");
      return;
    }
    try {
      const result = await api(`/api/items/${product.item_id}/orders`, "POST");
      setOrders((current) => [result.order, ...current]);
      setProducts((current) => current.map((item) => item.item_id === product.item_id ? { ...item, my_order_status: "PENDING" } : item));
      setNotice("Your request has been sent to the seller.");
      navigate("/orders");
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function changeOrderStatus(orderId, nextStatus) {
    try {
      const result = await api(`/api/orders/${orderId}`, "PATCH", { status: nextStatus });
      setOrders((current) => current.map((order) => order.order_id === orderId ? result.order : order));
      setNotice(nextStatus === "CANCELLED" ? "Order cancelled." : `Order ${nextStatus.toLowerCase()}.`);
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function saveMeetupDate(order) {
    const meetupDate = meetupDrafts[order.order_id] ?? order.meetup_date ?? "";
    try {
      const result = await api(`/api/orders/${order.order_id}/meetup-date`, "PATCH", { meetup_date: meetupDate || null });
      setOrders((current) => current.map((item) => item.order_id === order.order_id ? result.order : item));
      setMeetupDrafts((current) => ({ ...current, [order.order_id]: result.order.meetup_date || "" }));
      setNotice(meetupDate ? "Meetup date saved." : "Meetup date cleared.");
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function markNotificationRead(notification) {
    if (notification.is_read) return;
    try {
      const result = await api(`/api/notifications/${notification.notification_id}/read`, "PATCH");
      setNotifications((current) => current.map((item) => item.notification_id === notification.notification_id ? result.notification : item));
      setUnreadNotifications((count) => Math.max(0, count - 1));
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function markAllNotificationsRead() {
    try {
      await api("/api/notifications/read-all", "POST");
      setNotifications((current) => current.map((notification) => ({ ...notification, is_read: true })));
      setUnreadNotifications(0);
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function submitAssistantQuestion(event) {
    event.preventDefault();
    const query = assistantDraft.trim();
    if (!query || assistantBusy) return;
    const userMessage = { id: crypto.randomUUID(), role: "user", content: query };
    const recentContext = [...assistantMessages, userMessage].slice(-7).map((message) => `${message.role === "user" ? "Student" : "Assistant"}: ${message.content}`).join("\n");
    setAssistantMessages((current) => [...current, userMessage]);
    setAssistantDraft("");
    setAssistantBusy(true);
    try {
      const result = await api("/api/assistant/chat", "POST", { query: recentContext.slice(-1900) });
      setAssistantMessages((current) => [...current, { id: crypto.randomUUID(), role: "assistant", content: result.reply, model: result.model }]);
    } catch (error) {
      setAssistantMessages((current) => [...current, { id: crypto.randomUUID(), role: "assistant", content: error.message, model: "unavailable" }]);
    } finally {
      setAssistantBusy(false);
    }
  }

  function resetAssistant() {
    setAssistantMessages([{ id: "welcome", role: "assistant", content: "Hi! I can help you list an item, understand an order, or find your way around Campus X Mart." }]);
    setAssistantDraft("");
  }

  async function uploadMedia(itemId, file) {
    if (!file) return;
    if (!hasVerifiedContact(user)) {
      navigate("/account");
      setNotice("Verify your email or phone number before adding listing media.");
      return;
    }
    const formData = new FormData();
    formData.append("file", file);
    try {
      const response = await fetch(`${API}/api/listings/${itemId}/media`, {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` },
        body: formData,
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "The upload could not be completed.");
      setItems((current) => current.map((item) => item.item_id === itemId ? { ...item, media_url: result.media.media_url } : item));
      setNotice("Photo added to your listing.");
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function sendCode() {
    try {
      const result = await api("/api/auth/send-verification", "POST", { channel });
      setNotice(result.dev_code ? `${result.message} Code: ${result.dev_code}` : result.message);
      setResendIn(result.resend_after_seconds || 60);
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function verifyCode(event) {
    event.preventDefault();
    try {
      const result = await api("/api/auth/verify", "POST", { channel, code });
      setNotice(result.message);
      setUser((current) => ({ ...current, [channel === "EMAIL" ? "email_verified" : "phone_verified"]: true }));
      setCode("");
    } catch (error) {
      setNotice(error.message);
    }
  }

  function logout() {
    localStorage.removeItem("access_token");
    setUser(null);
    setItems([]);
    navigate("/");
  }

  if (!authReady) return <Localized language={language}><main className="loading-screen"><span className="loading-mark">cXm</span><p>Opening your campus market…</p></main></Localized>;
  if (!user && route === "/") return <Landing language={language} onLanguageChange={setLanguage} onNavigate={navigate} />;
  if (!user && (route === "/login" || route === "/register" || route === "/admin/login")) {
    return <AuthPage register={route === "/register"} adminLogin={route === "/admin/login"} onNavigate={navigate} onSubmit={handleAuth} busy={busy} notice={notice} language={language} onLanguageChange={setLanguage} />;
  }

  const availableCount = items.filter((item) => item.status === "AVAILABLE").length;
  const verified = hasVerifiedContact(user);
  const visibleItems = items.filter((item) => {
    const matchesText = `${item.name} ${item.category} ${item.description}`.toLowerCase().includes(search.toLowerCase());
    return matchesText && (statusFilter === "ALL" || item.status === statusFilter);
  });
  const pageTitle = navigation.find((item) => item.path === route)?.label || "Overview";
  const activePeer = conversations.find((conversation) => conversation.user_id === selectedConversation) || selectedPeer;
  const categorySuggestion = suggestCategory(`${listing.name} ${listing.description}`);
  const selectedLocation = locations.find((location) => location.location_id === Number(listing.location_id));
  const locationQuery = buildLocationQuery(selectedLocation);
  const mapEmbedUrl = locationQuery ? googleMapsEmbedUrl(selectedLocation) : "";
  const mapLinkUrl = locationQuery ? googleMapsSearchUrl(selectedLocation) : "";

  return (
    <Localized language={language}><div className="app-shell">
      <aside className="app-sidebar">
        <div className="sidebar-header">
          <button className="sidebar-brand" onClick={() => navigate("/")}><Brand /></button>
        </div>
        <div className="sidebar-section-label">WORKSPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          {navigation.filter((item) => item.path !== "/admin/moderation" || user?.admin_session).map((item) => (
            <button key={item.path} className={`side-link${route === item.path ? " side-link-active" : ""}`} onClick={() => navigate(item.path)}>
              <span className="side-index">{item.index}</span><span>{item.label}</span>{item.path === "/notifications" && unreadNotifications > 0 && <span className="notification-badge">{unreadNotifications > 99 ? "99+" : unreadNotifications}</span>}{item.path === "/account" && !verified && <span className="side-dot" aria-label="Verification needed" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-user-mark">{user?.full_name?.slice(0, 1).toUpperCase() || "S"}</div>
          <div className="sidebar-user-copy"><strong>{user?.full_name || user?.username}</strong><span>{user?.email}</span></div>
          <button className="logout-button" onClick={logout} aria-label="Log out">↗</button>
        </div>
      </aside>

      {mobileMenuOpen && <>
        <button className="mobile-menu-backdrop" aria-label="Close navigation menu" onClick={() => setMobileMenuOpen(false)} />
        <aside className="mobile-drawer" id="mobile-menu-panel" aria-label="Main menu">
          <header className="mobile-drawer-header">
            <Brand />
            <button className="mobile-drawer-close" aria-label="Close menu" onClick={() => setMobileMenuOpen(false)}>×</button>
          </header>
          <p className="mobile-drawer-heading">CAMPUS X MART</p>
          <nav className="mobile-drawer-nav" aria-label="All sections">
            {navigation.filter((item) => item.path !== "/admin/moderation" || user?.admin_session).map((item) => (
              <button key={item.path} className={`mobile-drawer-link${route === item.path ? " mobile-drawer-link-active" : ""}`} aria-current={route === item.path ? "page" : undefined} onClick={() => navigate(item.path)}>
                <span className="mobile-drawer-index">{item.index}</span><span>{item.label}</span>{item.path === "/notifications" && unreadNotifications > 0 && <span className="notification-badge">{unreadNotifications > 99 ? "99+" : unreadNotifications}</span>}{item.path === "/account" && !verified && <span className="side-dot" aria-label="Verification needed" />}
              </button>
            ))}
          </nav>
          <div className="mobile-drawer-account">
            <span className="sidebar-user-mark">{user?.full_name?.slice(0, 1).toUpperCase() || "S"}</span>
            <span className="mobile-drawer-user">{user?.full_name || user?.username}</span>
            <button className="mobile-menu-logout" onClick={logout}>Log out</button>
          </div>
        </aside>
      </>}

      <nav className="mobile-bottom-nav" aria-label="Primary navigation">
        {mobileNavigation.map((item) => (
          <button key={item.path} className={`mobile-tab${route === item.path ? " mobile-tab-active" : ""}`} aria-current={route === item.path ? "page" : undefined} onClick={() => navigate(item.path)}>
            <span className={`mobile-tab-icon${item.path === "/notifications" ? " mobile-tab-icon-alert" : ""}`} aria-hidden="true">{item.icon}</span>
            <span>{item.label}</span>
            {item.path === "/notifications" && unreadNotifications > 0 && <span className="mobile-tab-badge">{unreadNotifications > 99 ? "99+" : unreadNotifications}</span>}
          </button>
        ))}
        <button className={`mobile-tab${mobileMenuOpen || !mobileNavigation.some((item) => item.path === route) ? " mobile-tab-active" : ""}`} aria-label="Open menu" aria-expanded={mobileMenuOpen} aria-controls="mobile-menu-panel" onClick={() => setMobileMenuOpen((open) => !open)}>
          <span className="hamburger-mark" aria-hidden="true"><i /><i /><i /></span><span>Menu</span>
        </button>
      </nav>

      <main className="workspace-main">
        <header className="workspace-topbar">
          <span><span className="topbar-label">CAMPUS X MART</span><span className="topbar-divider">/</span>{pageTitle}</span>
          <div className="topbar-actions">
            <LanguageSwitcher value={language} onChange={setLanguage} />
            <button className="topbar-account" onClick={() => navigate("/account")}><span className="online-dot" /> Account</button>
          </div>
        </header>
        <div className="workspace-content">
          {notice && <div className="notice notice-inline" role="status"><span>{notice}</span><button onClick={() => setNotice("")} aria-label="Dismiss message">×</button></div>}

          {route === "/" && <>
            <PageHeading kicker="YOUR CAMPUS MARKETPLACE" title={`Good ${new Date().getHours() < 12 ? "morning" : new Date().getHours() < 18 ? "afternoon" : "evening"}, ${user?.full_name?.split(" ")[0] || "there"}.`} detail="A little space to keep your campus selling simple." action={<button className="button button-dark" onClick={() => { setListing(blankListing); setEditingId(null); navigate("/sell"); }}>＋ Sell an item</button>} />
            <section className="stats-row" aria-label="Marketplace overview">
              <article className="stat-block stat-feature"><span className="stat-label">YOUR LISTINGS</span><strong>{items.length.toString().padStart(2, "0")}</strong><span>Everything you’ve put up for sale</span></article>
              <article className="stat-block"><span className="stat-label">AVAILABLE</span><strong>{availableCount.toString().padStart(2, "0")}</strong><span>Ready for a new owner</span></article>
              <article className="stat-block"><span className="stat-label">ACCOUNT</span><strong className={`stat-word${verified ? " is-verified" : ""}`}>{verified ? "Verified" : "In progress"}</strong><span>{verified ? "You’re cleared to sell" : "Finish verification to sell"}</span></article>
            </section>
            <div className="section-heading"><div><p className="eyebrow">A QUICK LOOK</p><h2>Recently listed</h2></div><button className="inline-link" onClick={() => navigate("/listings")}>All your listings <span aria-hidden="true">→</span></button></div>
            {items.length ? <div className="recent-list">{items.slice(0, 3).map((item) => <ListingRow key={item.item_id} item={item} onEdit={startEditing} onDelete={deleteListing} onUpload={uploadMedia} language={language} />)}</div> : <section className="empty-state"><span className="empty-number">01</span><div><h3>Your first item starts here.</h3><p>Give a useful item a second life with your campus community.</p></div><button className="button button-outline" onClick={() => navigate("/sell")}>Sell an item <span aria-hidden="true">→</span></button></section>}
          </>}

          {route === "/products" && <>
            <PageHeading kicker="FROM YOUR CAMPUS" title="Products" detail={verified ? "Find something useful. Ask the seller. Keep it local." : "Verify your email or phone to request a purchase."} action={!verified && <button className="button button-dark" onClick={() => navigate("/account")}>Verify contact <span aria-hidden="true">↗</span></button>} />
            <div className="product-toolbar">
              <label className="search-control"><span aria-hidden="true">⌕</span><input aria-label="Search products" placeholder="Search products" value={productSearch} onChange={(event) => { setProductSearch(event.target.value); setProductPage(1); }} /></label>
              <label className="filter-control"><span className="visually-hidden">Filter products by category</span><select value={productCategory} onChange={(event) => { setProductCategory(event.target.value); setProductPage(1); }}><option value="">All categories</option>{categories.map((category) => <option key={category} value={category} data-no-translate>{category}</option>)}</select></label>
              <label className="filter-control"><span className="visually-hidden">Filter products by condition</span><select value={productCondition} onChange={(event) => { setProductCondition(event.target.value); setProductPage(1); }}><option value="">Any condition</option><option value="NEW">New</option><option value="USED_EXCELLENT">Used - excellent</option><option value="USED_GOOD">Used - good</option><option value="USED">Used</option></select></label>
              <label className="price-filter"><span>Min ৳</span><input type="number" min="0" max={productMaxPrice || undefined} aria-label="Minimum price" value={productMinPrice} onChange={(event) => { setProductMinPrice(event.target.value); setProductPage(1); }} /></label>
              <label className="price-filter"><span>Max ৳</span><input type="number" min={productMinPrice || 0} aria-label="Maximum price" value={productMaxPrice} onChange={(event) => { setProductMaxPrice(event.target.value); setProductPage(1); }} /></label>
              <label className="filter-control sort-control"><span className="visually-hidden">Sort products</span><select value={productSort} onChange={(event) => { setProductSort(event.target.value); setProductPage(1); }}><option value="newest">Newest</option><option value="price_asc">Price: low to high</option><option value="price_desc">Price: high to low</option><option value="name_asc">Name: A to Z</option></select></label>
              <button className="clear-filters" onClick={() => { setProductSearch(""); setProductCategory(""); setProductCondition(""); setProductMinPrice(""); setProductMaxPrice(""); setProductSort("newest"); setProductPage(1); }}>Clear</button>
            </div>
            <div className="product-results-meta"><span>{productTotal ? `${(productPage - 1) * PRODUCT_PAGE_SIZE + 1}–${Math.min(productPage * PRODUCT_PAGE_SIZE, productTotal)} of ${productTotal}` : "0 results"}</span><span>Products for your campus</span></div>
            {products.length ? <div className="product-grid">{products.map((product) => <article className="product-card" key={product.item_id}>
              <div className="product-photo-wrap">{product.media_url ? <img className="product-photo" src={product.media_url} alt={product.name} loading="lazy" /> : <div className="product-photo product-photo-empty" aria-hidden="true"><span>{product.category.slice(0, 1).toUpperCase()}</span></div>}<span className="product-category" data-no-translate>{product.category}</span></div>
              {youtubeEmbedUrl(product.video_url) && <div className="product-video-frame"><iframe src={youtubeEmbedUrl(product.video_url)} title={`Video for ${product.name}`} loading="lazy" referrerPolicy="strict-origin-when-cross-origin" sandbox="allow-scripts allow-same-origin allow-presentation" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowFullScreen /></div>}
              <div className="product-card-body"><div className="product-seller"><span className="seller-avatar">{product.seller.full_name.slice(0, 1).toUpperCase()}</span><span data-no-translate>{product.seller.full_name}</span></div><h2 data-no-translate>{product.name}</h2><p className="product-description" data-no-translate>{product.description}</p><div className="product-meta"><strong>{money(product.price, language)}</strong><span>{translate(product.item_condition.replaceAll("_", " ").toLowerCase().replace("used_", "used "), language)}</span></div>
                {product.location && <div className="product-location"><span data-no-translate><span aria-hidden="true">⌖</span>{product.location.location_name}{product.location.campus_name ? ` · ${product.location.campus_name}` : ""}</span><a href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(product.location.latitude != null && product.location.longitude != null ? `${product.location.latitude},${product.location.longitude}` : [product.location.location_name, product.location.campus_name, product.location.address].filter(Boolean).join(", "))}`} target="_blank" rel="noreferrer">Map ↗</a></div>}
                <div className="product-rating-summary"><RatingStars rating={product.average_rating ?? product.seller_rating} language={language} /><span>{product.average_rating !== null ? `${product.average_rating} · ${product.review_count} ${product.review_count === 1 ? "review" : "reviews"}` : product.seller_rating !== null ? `Seller ${product.seller_rating}` : "No reviews yet"}</span></div>
                <div className="product-actions"><button className={`product-action${product.current_reaction === "LIKE" ? " product-action-liked" : ""}`} aria-label={`${product.current_reaction === "LIKE" ? "Remove like" : "Like"} ${product.name}`} aria-pressed={product.current_reaction === "LIKE"} onClick={() => toggleProductReaction(product, "LIKE")}><span aria-hidden="true">{product.current_reaction === "LIKE" ? "♥" : "♡"}</span><span>Like {product.like_count}</span></button><button className={`product-action${product.current_reaction === "DISLIKE" ? " product-action-disliked" : ""}`} aria-label={`${product.current_reaction === "DISLIKE" ? "Remove dislike" : "Dislike"} ${product.name}`} aria-pressed={product.current_reaction === "DISLIKE"} onClick={() => toggleProductReaction(product, "DISLIKE")}><span aria-hidden="true">−</span><span>Dislike {product.dislike_count}</span></button><button className="product-action" aria-expanded={openComments === product.item_id} onClick={() => toggleProductComments(product.item_id)}><span aria-hidden="true">▤</span><span>{product.comment_count} comments</span></button><button className="product-action review-toggle" aria-expanded={openReviews === product.item_id} onClick={() => toggleProductReviews(product.item_id)}><span aria-hidden="true">★</span><span>{product.review_count} reviews</span></button>{product.seller.user_id !== user?.id && <><button className="message-seller" onClick={() => openConversationWith(product.seller)}>Message seller <span aria-hidden="true">↗</span></button><button className="order-product" onClick={() => requestProductOrder(product)} disabled={product.my_order_status === "PENDING"}>{product.my_order_status === "PENDING" ? "Request sent" : "Request to buy"}</button><button className="product-action report-toggle" onClick={() => { setReportingItem(reportingItem === product.item_id ? null : product.item_id); setReportReason(""); }}>Report</button></>}</div>
                {reportingItem === product.item_id && <form className="product-report-form" onSubmit={(event) => submitProductReport(event, product.item_id)}><label className="field" htmlFor={`report-reason-${product.item_id}`}><span>Why are you reporting this product?</span><textarea id={`report-reason-${product.item_id}`} value={reportReason} onChange={(event) => setReportReason(event.target.value)} placeholder="Describe the issue for the moderation team." minLength={5} maxLength={2000} required /></label><div><button type="button" className="button button-quiet" onClick={() => setReportingItem(null)}>Cancel</button><button className="button button-dark">Submit report</button></div></form>}
                {openComments === product.item_id && <section className="product-comments" aria-label={`Comments on ${product.name}`}><div className="comments-list">{(commentsByItem[product.item_id] || []).length ? commentsByItem[product.item_id].map((comment) => <article className="product-comment" key={comment.comment_id}><strong data-no-translate>{comment.author.full_name}</strong><p data-no-translate>{comment.comment_text}</p></article>) : <p className="comments-empty">No comments yet. Start the conversation.</p>}</div><form className="comment-compose" onSubmit={(event) => submitProductComment(event, product.item_id)}><input aria-label={`Write a comment on ${product.name}`} placeholder="Ask a question…" value={commentDrafts[product.item_id] || ""} onChange={(event) => setCommentDrafts((current) => ({ ...current, [product.item_id]: event.target.value }))} maxLength={1000} required /><button aria-label="Post comment">↑</button></form></section>}
                {openReviews === product.item_id && <section className="product-reviews" aria-label={`Reviews for ${product.name}`}><div className="reviews-summary"><RatingStars rating={reviewsByItem[product.item_id]?.average_rating} language={language} /><span>{reviewsByItem[product.item_id]?.average_rating ?? "No rating"} · {reviewsByItem[product.item_id]?.review_count ?? 0} reviews</span></div>{(reviewsByItem[product.item_id]?.reviews || []).length ? reviewsByItem[product.item_id].reviews.map((review) => <article className="product-review" key={review.review_id}><div><strong data-no-translate>{review.author.full_name}</strong><RatingStars rating={review.rating} language={language} /></div>{review.review_text && <p data-no-translate>{review.review_text}</p>}</article>) : <p className="comments-empty">No reviews yet.</p>}<p className="seller-rating-note">Seller rating: {reviewsByItem[product.item_id]?.seller_rating ?? "No rating yet"}</p></section>}
              </div>
            </article>)}</div> : <section className="empty-state"><span className="empty-number">00</span><div><h3>No products found.</h3><p>Try another search, or be the first to share something with campus.</p></div><button className="button button-outline" onClick={() => navigate("/sell")}>Sell an item <span aria-hidden="true">→</span></button></section>}
            {productTotal > PRODUCT_PAGE_SIZE && <nav className="product-pagination" aria-label="Product pages"><span>Page {productPage} of {Math.ceil(productTotal / PRODUCT_PAGE_SIZE)}</span><div><button className="button button-outline" disabled={productPage <= 1} onClick={() => setProductPage((page) => Math.max(1, page - 1))}>← Previous</button><button className="button button-outline" disabled={productPage >= Math.ceil(productTotal / PRODUCT_PAGE_SIZE)} onClick={() => setProductPage((page) => Math.min(Math.ceil(productTotal / PRODUCT_PAGE_SIZE), page + 1))}>Next →</button></div></nav>}
          </>}

          {route === "/messages" && <>
            <PageHeading kicker="PRIVATE CONVERSATIONS" title="Messages" detail="Talk directly with students about products and meetups." />
            <section className="messages-workspace">
              <aside className="conversation-list" aria-label="Conversations"><div className="conversation-list-heading"><span>INBOX</span><span>{conversations.length}</span></div>
                <div className="user-search">
                  <label htmlFor="message-user-search">Start a conversation</label>
                  <input id="message-user-search" type="search" placeholder="Search people by name or username" value={userSearch} onChange={(event) => setUserSearch(event.target.value)} />
                </div>
                {userSearch.trim().length >= 2 && <div className="user-search-results" aria-live="polite">
                  {searchingUsers ? <p className="user-search-status">Searching people…</p> : userSearchResults.length ? userSearchResults.map((person) => <button key={person.user_id} className="conversation-choice user-search-result" onClick={() => { setUserSearch(""); setUserSearchResults([]); openConversationWith(person); }}><span className="conversation-avatar">{person.full_name.slice(0, 1).toUpperCase()}</span><span className="conversation-summary"><strong>{person.full_name}</strong><span>@{person.username}</span></span><span className="user-search-action">Chat</span></button>) : <p className="user-search-status">No matching people found.</p>}
                </div>}
                {conversations.map((conversation) => <button key={conversation.user_id} className={`conversation-choice${selectedConversation === conversation.user_id ? " conversation-choice-active" : ""}`} onClick={() => { setSelectedConversation(conversation.user_id); setSelectedPeer(conversation); }}><span className="conversation-avatar">{conversation.full_name.slice(0, 1).toUpperCase()}</span><span className="conversation-summary"><strong data-no-translate>{conversation.full_name}</strong><span data-no-translate>{conversation.last_message}</span></span>{conversation.unread_count > 0 && <span className="unread-count">{conversation.unread_count}</span>}</button>)}
                {selectedPeer && !conversations.some((conversation) => conversation.user_id === selectedPeer.user_id) && <button className="conversation-choice conversation-choice-active" onClick={() => setSelectedConversation(selectedPeer.user_id)}><span className="conversation-avatar">{selectedPeer.full_name.slice(0, 1).toUpperCase()}</span><span className="conversation-summary"><strong>{selectedPeer.full_name}</strong><span>New conversation</span></span></button>}
                {!conversations.length && !selectedPeer && <p className="inbox-empty">Your conversations will show up here.</p>}
              </aside>
              <div className="message-panel">{activePeer ? <><header className="message-peer"><span className="conversation-avatar">{activePeer.full_name.slice(0, 1).toUpperCase()}</span><div><strong data-no-translate>{activePeer.full_name}</strong><span data-no-translate>@{activePeer.username}</span></div></header><div className="message-thread" aria-live="polite">{messages.length ? messages.map((message) => <article key={message.message_id} className={`message-bubble${message.sender_id === user?.id ? " message-bubble-own" : ""}`}><p data-no-translate>{message.message_text}</p><div className="message-bubble-meta"><time>{new Date(message.sent_at).toLocaleTimeString(language === "bn" ? "bn-BD" : "en-BD", { hour: "numeric", minute: "2-digit" })}</time><button type="button" className="message-delete" onClick={() => hideMessage(message.message_id)}>{translate("Delete for me", language)}</button></div></article>) : <p className="thread-empty">{translate("Start with a question about an item or a time to meet.", language)}</p>}</div><form className="message-compose" onSubmit={sendMessage}><input aria-label="Write a message" placeholder="Write a message…" value={messageDraft} onChange={(event) => setMessageDraft(event.target.value)} maxLength={2000} required /><button className="button button-dark" disabled={!messageDraft.trim()}>Send <span aria-hidden="true">↗</span></button></form></> : <div className="message-empty"><span className="empty-number">01</span><h2>Your next conversation starts with a product.</h2><p>Open the products page and message a seller to ask a question.</p><button className="button button-outline" onClick={() => navigate("/products")}>Explore products <span aria-hidden="true">→</span></button></div>}</div>
            </section>
          </>}

          {route === "/assistant" && <>
            <PageHeading kicker="CAMPUS X MART GUIDE" title="Marketplace assistant" detail="Ask about listing, buying, orders, or account setup." action={<button className="button button-outline" onClick={resetAssistant}>New conversation</button>} />
            <section className="assistant-shell"><div className="assistant-heading"><span className="assistant-mark" aria-hidden="true">XM</span><div><strong>Campus X Mart assistant</strong><span>Marketplace help, in plain language</span></div><span className="assistant-status"><i /> Ready</span></div><div className="assistant-thread" aria-live="polite" aria-label="Assistant conversation">{assistantMessages.map((message) => <article key={message.id} className={`assistant-message assistant-message-${message.role}`}><div className="assistant-avatar">{message.role === "user" ? user?.full_name?.slice(0, 1).toUpperCase() : "XM"}</div><div className="assistant-message-content"><p data-no-translate>{message.id === "welcome" ? translate(message.content, language) : message.content}</p>{message.model && <span className={`assistant-source${message.model === "rule-based-fallback" ? " assistant-source-demo" : message.model === "unavailable" ? " assistant-source-error" : ""}`}>{message.model === "rule-based-fallback" ? "Demo guide" : message.model === "unavailable" ? "Unavailable" : `AI · ${message.model}`}</span>}</div></article>)}{assistantBusy && <div className="assistant-typing"><span /><span /><span /> Thinking</div>}<div ref={assistantScrollRef} /></div><div className="assistant-composer-area"><div className="assistant-suggestions"><span>TRY ASKING</span>{["How do I sell an item?", "How does an order work?", "How do I verify my account?"].map((prompt) => <button key={prompt} onClick={() => setAssistantDraft(prompt)}>{prompt}</button>)}</div><form className="assistant-composer" onSubmit={submitAssistantQuestion}><textarea aria-label="Ask the marketplace assistant" placeholder="Ask a marketplace question…" value={assistantDraft} onChange={(event) => setAssistantDraft(event.target.value)} maxLength={1900} rows={2} /><button className="button button-dark" disabled={assistantBusy || !assistantDraft.trim()}>{assistantBusy ? "Thinking…" : "Send"}<span aria-hidden="true">↗</span></button></form><p className="assistant-disclaimer">Replies may use AI or a limited demo guide, depending on configuration.</p></div></section>
          </>}

          {route === "/notifications" && <>
            <PageHeading kicker="ACTIVITY ON CAMPUS" title="Notifications" detail="Messages, comments, and order updates in one place." action={unreadNotifications > 0 && <button className="button button-outline" onClick={markAllNotificationsRead}>Mark all read</button>} />
            <div className="notifications-toolbar"><div className="orders-tabs" role="group" aria-label="Filter notifications">{[["ALL", "All"], ["UNREAD", "Unread"]].map(([value, label]) => <button key={value} className={notificationFilter === value ? "orders-tab orders-tab-active" : "orders-tab"} onClick={() => setNotificationFilter(value)}>{label}</button>)}</div><span>{unreadNotifications} unread</span></div>
            {notifications.filter((notification) => notificationFilter === "ALL" || !notification.is_read).length ? <div className="notification-list">{notifications.filter((notification) => notificationFilter === "ALL" || !notification.is_read).map((notification) => <article className={`notification-item${notification.is_read ? " notification-read" : " notification-unread"}`} key={notification.notification_id}><span className={`notification-symbol notification-symbol-${notification.notification_type.toLowerCase()}`} aria-hidden="true">{notification.notification_type === "MESSAGE" ? "✉" : notification.notification_type === "ORDER" ? "↔" : "▤"}</span><div className="notification-copy"><div className="notification-title-row"><h2>{translateNotification(notification.title, language)}</h2><time>{new Date(notification.created_at).toLocaleString(language === "bn" ? "bn-BD" : "en-BD")}</time></div><p>{translateNotification(notification.message, language)}</p><button className="inline-link" onClick={async () => { await markNotificationRead(notification); if (notification.target_url) navigate(notification.target_url); }}>{notification.target_url ? "Open" : "View"} <span aria-hidden="true">→</span></button></div>{!notification.is_read && <span className="notification-unread-dot" aria-label="Unread" />}</article>)}</div> : <section className="empty-state"><span className="empty-number">00</span><div><h3>{notificationFilter === "UNREAD" ? "You’re all caught up." : "No notifications yet."}</h3><p>Updates about messages, comments, and orders will appear here.</p></div></section>}
          </>}

          {route === "/admin/moderation" && (user?.admin_session ? <>
            <PageHeading kicker="ADMIN WORKSPACE" title="Moderation" detail="Review reports and manage who can post to the marketplace." />
            <div className="moderation-view-tabs" role="group" aria-label="Moderation sections">
              <button className={moderationTab === "REPORTS" ? "orders-tab orders-tab-active" : "orders-tab"} onClick={() => setModerationTab("REPORTS")}>Reports</button>
              <button className={moderationTab === "USERS" ? "orders-tab orders-tab-active" : "orders-tab"} onClick={() => setModerationTab("USERS")}>Posting access</button>
            </div>
            {moderationTab === "REPORTS" ? <>
              <div className="moderation-toolbar"><div className="orders-tabs" role="group" aria-label="Filter reports">{[["OPEN", "Open reports"], ["REVIEWING", "Reviewing"], ["RESOLVED", "Resolved"], ["REJECTED", "Rejected"], ["ALL", "All"]].map(([value, label]) => <button key={value} className={reportStatusFilter === value ? "orders-tab orders-tab-active" : "orders-tab"} onClick={() => setReportStatusFilter(value)}>{label}</button>)}</div><span>{reports.length} reports</span></div>
              {reports.length ? <div className="moderation-list">{reports.map((report) => <ModerationCard key={report.report_id} report={report} onSetStatus={setModerationStatus} language={language} />)}</div> : <section className="empty-state"><span className="empty-number">00</span><div><h3>No reports in this queue.</h3><p>New product reports will appear here.</p></div></section>}
            </> : <section className="admin-users-panel">
              <div className="admin-users-controls">
                <label className="search-control"><span aria-hidden="true">⌕</span><input type="search" aria-label="Search users by name or username" placeholder="Search name or username" value={adminUserSearch} onChange={(event) => setAdminUserSearch(event.target.value)} /></label>
                <label className="field"><span>Reason for ban</span><input value={adminBanReason} onChange={(event) => setAdminBanReason(event.target.value)} maxLength={500} placeholder="Required when banning a user" /></label>
              </div>
              {adminUserSearch.trim().length < 2 ? <p className="admin-users-hint">Search by at least two characters. Only student accounts are listed.</p> : adminUsersLoading ? <p className="admin-users-hint">Searching accounts…</p> : adminUsers.length ? <div className="admin-users-list">{adminUsers.map((person) => <article className="admin-user-row" key={person.user_id}><div className="admin-user-identity"><strong>{person.full_name}</strong><span>@{person.username}</span></div><div className="admin-user-ban-state">{person.posting_banned ? <><strong>Banned from posting</strong><span>{person.posting_ban_reason}</span></> : <span>Posting allowed</span>}</div><button className={person.posting_banned ? "button button-outline" : "button button-text-danger"} disabled={!person.posting_banned && adminBanReason.trim().length < 5} onClick={() => updatePostingBan(person)}>{person.posting_banned ? "Unban" : "Ban from posting"}</button></article>)}</div> : <p className="admin-users-hint">No matching student accounts.</p>}
            </section>}
          </> : <section className="empty-state"><span className="empty-number">403</span><div><h3>Admin access required.</h3><p>This moderation workspace is restricted to administrators.</p></div><button className="button button-outline" onClick={() => navigate("/")}>Back to overview</button></section>)}

          {route === "/orders" && <>
            <PageHeading kicker="BUYING & SELLING" title="Orders" detail="Track requests, confirm meetups, and close completed exchanges." action={<button className="button button-dark" onClick={() => navigate("/products")}>Explore products <span aria-hidden="true">↗</span></button>} />
            <div className="orders-toolbar"><div className="orders-tabs" role="group" aria-label="Filter orders">{[["ALL", "All"], ["BUYER", "Buying"], ["SELLER", "Selling"]].map(([value, label]) => <button key={value} className={orderStatus === value ? "orders-tab orders-tab-active" : "orders-tab"} onClick={() => setOrderStatus(value)}>{label}</button>)}</div><span>{orders.length} {orders.length === 1 ? "order" : "orders"}</span></div>
            {orders.filter((order) => orderStatus === "ALL" || order.current_user_role === orderStatus).length ? <div className="orders-list">{orders.filter((order) => orderStatus === "ALL" || order.current_user_role === orderStatus).map((order) => {
              const isBuyer = order.current_user_role === "BUYER";
              const otherParty = isBuyer ? order.seller : order.buyer;
              return <article className="order-card" key={order.order_id}><div className="order-card-main"><div className="order-topline"><span className={`order-state order-state-${order.status.toLowerCase()}`}>{order.status.toLowerCase()}</span><span className="order-reference">ORDER #{String(order.order_id).padStart(5, "0")}</span></div><h2>{order.item_name}</h2><p>{isBuyer ? "Seller" : "Buyer"}: <strong>{otherParty.full_name}</strong></p><div className="order-footer"><strong>{money(order.agreed_price, language)}</strong><span>{new Date(order.ordered_at).toLocaleDateString(language === "bn" ? "bn-BD" : "en-BD")}</span></div>{order.meetup_date && <p className="order-saved-date">Meetup date: <strong>{new Date(`${order.meetup_date}T00:00:00`).toLocaleDateString(language === "bn" ? "bn-BD" : "en-BD")}</strong></p>}</div><div className="order-card-actions">{["PENDING", "CONFIRMED"].includes(order.status) && <div className="order-meetup-control"><label className="field" htmlFor={`meetup-date-${order.order_id}`}><span>Meetup date</span><input id={`meetup-date-${order.order_id}`} type="date" min={localDateInputValue()} value={meetupDrafts[order.order_id] ?? order.meetup_date ?? ""} onChange={(event) => setMeetupDrafts((current) => ({ ...current, [order.order_id]: event.target.value }))} /></label><button className="button button-outline" disabled={(meetupDrafts[order.order_id] ?? order.meetup_date ?? "") === (order.meetup_date || "")} onClick={() => saveMeetupDate(order)}>Save date</button></div>}{order.status === "PENDING" && !isBuyer && <><button className="button button-dark" onClick={() => changeOrderStatus(order.order_id, "CONFIRMED")}>Confirm</button><button className="button button-outline" onClick={() => changeOrderStatus(order.order_id, "CANCELLED")}>Decline</button></>}{order.status === "PENDING" && isBuyer && <button className="button button-outline" onClick={() => changeOrderStatus(order.order_id, "CANCELLED")}>Cancel request</button>}{order.status === "CONFIRMED" && <><span className="reserved-note">Item reserved</span>{!isBuyer && <button className="button button-dark" onClick={() => changeOrderStatus(order.order_id, "COMPLETED")}>Mark completed</button>}<button className="button button-outline" onClick={() => changeOrderStatus(order.order_id, "CANCELLED")}>Cancel order</button></>}{(order.status === "CANCELLED" || order.status === "COMPLETED") && <span className="order-finished">{order.status === "COMPLETED" ? "Exchange complete" : "Request closed"}</span>}{order.status === "COMPLETED" && isBuyer && <button className="button button-outline" onClick={() => startOrderReview(order)}>{reviewsByItem[order.item_id]?.my_review ? "Edit review" : "Leave a review"}</button>}</div>{reviewingOrder === order.order_id && <form className="order-review-form" onSubmit={(event) => submitOrderReview(event, order)}><div className="review-form-heading"><div><strong>Your experience</strong><span>How was this exchange?</span></div><RatingStars rating={ratingDrafts[order.item_id] || 5} onChange={(rating) => setRatingDrafts((current) => ({ ...current, [order.item_id]: rating }))} label={`Rate ${order.item_name}`} language={language} /></div><textarea aria-label="Write your review" placeholder="Share a helpful note about the item and exchange." value={reviewDrafts[order.item_id] || ""} onChange={(event) => setReviewDrafts((current) => ({ ...current, [order.item_id]: event.target.value }))} maxLength={1200} /><div className="review-form-actions"><span>{(reviewDrafts[order.item_id] || "").length}/1200</span><button className="button button-dark">Save review</button></div></form>}</article>;
            })}</div> : <section className="empty-state"><span className="empty-number">00</span><div><h3>No orders here yet.</h3><p>{orderStatus === "SELLER" ? "Requests for your products will appear here." : "Browse campus products to get started."}</p></div><button className="button button-outline" onClick={() => navigate("/products")}>Explore products <span aria-hidden="true">→</span></button></section>}
          </>}

          {route === "/listings" && <>
            <PageHeading kicker="SELLER WORKSPACE" title="Your listings" detail="Keep track of what you’ve shared with campus." action={<button className="button button-dark" onClick={() => { setListing(blankListing); setEditingId(null); navigate("/sell"); }}>＋ Sell an item</button>} />
            <div className="list-controls"><label className="search-control"><span aria-hidden="true">⌕</span><input aria-label="Search your listings" placeholder="Search your listings" value={search} onChange={(event) => setSearch(event.target.value)} /></label><label className="filter-control"><span className="visually-hidden">Filter by status</span><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="ALL">All statuses</option><option value="AVAILABLE">Available</option><option value="DRAFT">Draft</option><option value="RESERVED">Reserved</option><option value="SOLD">Sold</option><option value="ARCHIVED">Archived</option></select></label></div>
            {visibleItems.length ? <div className="listing-table">{visibleItems.map((item) => <ListingRow key={item.item_id} item={item} onEdit={startEditing} onDelete={deleteListing} onUpload={uploadMedia} language={language} />)}</div> : <section className="empty-state"><span className="empty-number">{items.length ? "00" : "01"}</span><div><h3>{items.length ? "No listings match that." : "Nothing listed yet."}</h3><p>{items.length ? "Try another search or status." : "Sell an item to get your campus shop started."}</p></div>{!items.length && <button className="button button-outline" onClick={() => navigate("/sell")}>Sell an item <span aria-hidden="true">→</span></button>}</section>}
          </>}

          {route === "/sell" && <>
            <PageHeading kicker="SELL SOMETHING USEFUL" title={editingId ? "Edit your item" : "Sell an item"} detail={verified ? "A clear description helps the right person find it." : "Verify your email or phone before posting a listing."} action={!verified && <button className="button button-dark" onClick={() => navigate("/account")}>Verify contact <span aria-hidden="true">↗</span></button>} />
            <form className="listing-editor" onSubmit={saveListing}>
              <div className="editor-main">
                <Field id="listing-name" label="What are you selling?" name="name" placeholder="e.g. Calculus textbook, barely used" value={listing.name} onChange={updateListing} required minLength={2} maxLength={150} />
                <Field id="listing-description" label="Description" name="description" multiline placeholder="Share the details a buyer should know." value={listing.description} onChange={updateListing} required minLength={10} maxLength={5000} />
                <div className="video-url-field"><Field id="listing-video-url" label="YouTube video (optional)" name="video_url" type="url" placeholder="https://youtu.be/..." value={listing.video_url} onChange={updateListing} maxLength={500} /><small>Valid YouTube links appear as a video preview on the product card.</small></div>
                <div className="form-row">
                  <Field id="listing-price" label="Price (BDT)" name="price" type="number" min="0" step="1" placeholder="0" value={listing.price} onChange={updateListing} required />
                  <div className="category-suggestion-field"><Field id="listing-category" label="Category" name="category" placeholder="Books, electronics…" value={listing.category} onChange={updateListing} required minLength={2} maxLength={50} />{categorySuggestion && <div className="category-suggestion"><div><span>On-device keyword suggestion</span><strong>{categorySuggestion.category}</strong><small>Matched: {categorySuggestion.matchedKeywords.join(", ")}</small></div><button type="button" className="button button-outline" disabled={listing.category === categorySuggestion.category} onClick={() => setListing((current) => ({ ...current, category: categorySuggestion.category }))}>{listing.category === categorySuggestion.category ? "Selected" : "Use suggestion"}</button></div>}</div>
                </div>
                <div className="form-row">
                  <label className="field" htmlFor="listing-condition"><span>Condition</span><select id="listing-condition" name="item_condition" value={listing.item_condition} onChange={updateListing}><option value="NEW">New</option><option value="USED_EXCELLENT">Used - excellent</option><option value="USED_GOOD">Used - good</option><option value="USED">Used</option></select></label>
                  <label className="field" htmlFor="listing-status"><span>Listing status</span><select id="listing-status" name="status" value={listing.status} onChange={updateListing}><option value="AVAILABLE">Available</option><option value="DRAFT">Draft</option></select></label>
                </div>
                <Field id="listing-available" label="Available from (optional)" name="available_from" type="date" value={listing.available_from} onChange={updateListing} />
                <div className="location-field-row"><label className="field" htmlFor="listing-location"><span>Meetup location</span><select id="listing-location" name="location_id" value={listing.location_id} onChange={updateListing}><option value="">No location selected</option>{locations.map((location) => <option key={location.location_id} value={location.location_id}>{location.location_name}{location.campus_name ? ` · ${location.campus_name}` : ""}</option>)}</select></label><button type="button" className="button button-outline add-location-button" onClick={() => setLocationFormOpen((open) => !open)}>{locationFormOpen ? "Close" : "＋ Add location"}</button></div>
                {locationFormOpen && <div className="location-create-form"><div className="form-row"><Field id="new-location-name" label="Location name" name="location_name" placeholder="e.g. Library entrance" value={locationDraft.location_name} onChange={(event) => setLocationDraft((current) => ({ ...current, location_name: event.target.value }))} required minLength={1} maxLength={100} /><Field id="new-location-campus" label="Campus" name="campus_name" placeholder="Campus name" value={locationDraft.campus_name} onChange={(event) => setLocationDraft((current) => ({ ...current, campus_name: event.target.value }))} maxLength={100} /></div><Field id="new-location-address" label="Address or directions" name="address" placeholder="Building, street, or meeting point" value={locationDraft.address} onChange={(event) => setLocationDraft((current) => ({ ...current, address: event.target.value }))} /><div className="form-row"><Field id="new-location-latitude" label="Latitude (optional)" name="latitude" type="number" min="-90" max="90" step="any" placeholder="23.7806" value={locationDraft.latitude} onChange={(event) => setLocationDraft((current) => ({ ...current, latitude: event.target.value }))} /><Field id="new-location-longitude" label="Longitude (optional)" name="longitude" type="number" min="-180" max="180" step="any" placeholder="90.4070" value={locationDraft.longitude} onChange={(event) => setLocationDraft((current) => ({ ...current, longitude: event.target.value }))} /></div><div className="location-create-actions"><span>Coordinates enable a precise map preview.</span><button type="button" className="button button-dark" disabled={locationBusy} onClick={createLocation}>{locationBusy ? "Adding…" : "Add to campus locations"}</button></div></div>}
                {selectedLocation && <div className="map-preview"><div className="map-preview-heading"><div><strong>{selectedLocation.location_name}</strong><span>{selectedLocation.campus_name || selectedLocation.address || "Campus meetup point"}</span></div><a href={mapLinkUrl} target="_blank" rel="noreferrer">Open map ↗</a></div><iframe src={mapEmbedUrl} title={`Map for ${selectedLocation.location_name}`} loading="lazy" referrerPolicy="no-referrer-when-downgrade" /></div>}
                <div className="editor-actions"><button type="button" className="button button-quiet" onClick={() => { setListing(blankListing); setEditingId(null); navigate("/listings"); }}>Cancel</button><button className="button button-dark" disabled={busy || !verified}>{busy ? "Saving…" : !verified ? "Verify to publish" : editingId ? "Save changes" : "Publish item"}<span aria-hidden="true">↗</span></button></div>
              </div>
              <aside className="editor-note"><span className="note-mark">A good listing</span><h3>Clear beats clever.</h3><p>Use a specific title, be honest about condition, and mention any details you’d want to know as a buyer.</p><div className="note-rule" /><span className="note-small">YOUR ITEM. YOUR PRICE. YOUR CAMPUS.</span></aside>
            </form>
          </>}

          {route === "/account" && <>
            <PageHeading kicker="YOUR PROFILE" title="Account & verification" detail="Keep your contact details trusted and up to date." action={<button className="button button-outline" onClick={logout}>Sign out</button>} />
            <div className="account-grid">
              <section className="account-summary"><div className="profile-mark">{user?.full_name?.slice(0, 1).toUpperCase() || "S"}</div><p className="eyebrow">CAMPUS MEMBER</p><h2>{user?.full_name || user?.username}</h2><p>{user?.email}</p><span className="member-since">Username <strong>@{user?.username}</strong></span></section>
              <section className="verification-panel"><div className="verification-heading"><div><p className="eyebrow">ACCOUNT TRUST</p><h2>Verify a contact method</h2></div><span className={`verification-state${verified ? " verified" : ""}`}>{verified ? "Verified" : "Action needed"}</span></div><p className="verification-copy">Verify your email or phone number to build trust with other students.</p>
                <div className="verification-methods"><div className="method-row"><span className="method-number">01</span><div><strong>Email address</strong><span>{user?.email}</span></div><span className={`method-status${user?.email_verified ? " method-done" : ""}`}>{user?.email_verified ? "Verified" : "Not verified"}</span></div><div className="method-row"><span className="method-number">02</span><div><strong>Phone number</strong><span>{user?.phone || "No phone number added"}</span></div><span className={`method-status${user?.phone_verified ? " method-done" : ""}`}>{user?.phone_verified ? "Verified" : "Not verified"}</span></div></div>
                {!verified && <div className="verify-actions"><label className="field" htmlFor="verify-channel"><span>Send code to</span><select id="verify-channel" value={channel} onChange={(event) => { setChannel(event.target.value); setCode(""); }}><option value="EMAIL">Email</option><option value="PHONE" disabled={!user?.phone}>Phone</option></select></label><button className="button button-outline" onClick={sendCode} disabled={resendIn > 0}>{resendIn ? `Resend in ${resendIn}s` : "Send verification code"}</button></div>}
                {!verified && <form className="code-form" onSubmit={verifyCode}><Field id="verification-code" label="Six-digit code" name="code" value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="000000" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" required /><button className="button button-dark">Verify contact</button></form>}
              </section>
            </div>
          </>}
          <footer className="workspace-footer"><span>Campus X Mart</span><span>Keep useful things moving.</span></footer>
        </div>
      </main>
    </div></Localized>
  );
}
