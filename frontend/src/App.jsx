import { useEffect, useRef, useState } from "react";
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import "./App.css";

const API = "http://localhost:8000";
const COLORS = ["#f2b544", "#46c8b5", "#7aa2f7", "#e58bb0", "#b6a6ff", "#9ad26b"];
const FUNNEL = ["home", "product_detail", "cart", "checkout"];
const TABS = ["Overview", "Products", "Behavior", "System"];
const DBS = [
  { key: "mongodb", name: "MongoDB", role: "Orders and product catalog" },
  { key: "cassandra", name: "Cassandra", role: "Click-event time series" },
  { key: "redis", name: "Redis", role: "Live counters and sessions" },
  { key: "neo4j", name: "Neo4j", role: "User–product graph" },
];
const tip = {
  contentStyle: { background: "#1a2d39", border: "1px solid #243949", borderRadius: 8 },
  labelStyle: { color: "#8fa5b3" },
  itemStyle: { color: "#e8f0f4" },
};
const inr = (n) =>
  "₹" + Number(n || 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const get = (path) => fetch(`${API}${path}`).then((r) => r.json());
const axis = { stroke: "#8fa5b3", tickLine: false, axisLine: false };

export default function App() {
  const [tab, setTab] = useState("Overview");
  const [revenue, setRevenue] = useState(null);
  const [activeUsers, setActiveUsers] = useState(0);
  const [topProducts, setTopProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [clicks, setClicks] = useState(null);
  const [health, setHealth] = useState(null);
  const [recProduct, setRecProduct] = useState("");
  const [recs, setRecs] = useState(null);
  const [liveData, setLiveData] = useState([]);
  const [metric, setMetric] = useState("orders");
  const [liveOn, setLiveOn] = useState(true);
  const [status, setStatus] = useState("Checking...");
  const liveRef = useRef(true);

  async function loadCore() {
    try {
      const [rev, users, prods, ords] = await Promise.all([
        get("/api/revenue"), get("/api/active-users"),
        get("/api/top-products?limit=10"), get("/api/orders?limit=10"),
      ]);
      setRevenue(rev);
      setActiveUsers(users.active_users);
      setTopProducts(prods.top_products);
      setOrders(ords.orders);
      setStatus("Connected");
    } catch {
      setStatus("Backend offline");
    }
  }

  async function loadSlow() {
    get("/api/click-activity").then(setClicks).catch(() => {});
    get("/api/health").then(setHealth).catch(() => setHealth(null));
  }

  useEffect(() => {
    loadCore();
    loadSlow();
    const timer = setInterval(loadSlow, 10000);
    const socket = new WebSocket("ws://localhost:8000/ws/live-updates");
    socket.onmessage = (e) => {
      const d = JSON.parse(e.data);
      if (!liveRef.current || d.revenue_today === undefined) return;
      setRevenue((p) => ({ ...p, revenue_today: d.revenue_today, orders_today: d.orders_today }));
      setActiveUsers(d.active_users);
      setLiveData((p) => [...p, {
        t: Date.now(), time: new Date().toLocaleTimeString(),
        orders: d.orders_today, revenue: d.revenue_today, users: d.active_users,
      }].slice(-30));
      if (d.event === "new_order") loadCore();
    };
    return () => { clearInterval(timer); socket.close(); };
  }, []);

  useEffect(() => {
    if (!recProduct && topProducts.length) setRecProduct(topProducts[0].product_id);
  }, [topProducts, recProduct]);

  useEffect(() => {
    if (recProduct) get(`/api/recommendations?product_id=${recProduct}&limit=5`).then(setRecs).catch(() => setRecs(null));
  }, [recProduct]);

  function toggleLive() {
    setLiveOn((p) => { liveRef.current = !p; return !p; });
  }

  const totalOrders = revenue?.orders_today || 0;
  const totalRevenue = revenue?.revenue_today || 0;
  const aov = totalOrders ? totalRevenue / totalOrders : 0;
  const first = liveData[0], last = liveData[liveData.length - 1];
  const span = first && last ? (last.t - first.t) / 60000 : 0;
  const perMin = span > 0.15 ? (last.orders - first.orders) / span : null;

  const pages = FUNNEL.map((p) => ({
    page: p.replace("_", " "),
    clicks: clicks?.by_page?.find((x) => x.page === p)?.clicks || 0,
  }));
  const homeClicks = pages[0].clicks || 1;
  const pieData = topProducts.slice(0, 6).map((p) => ({ name: p.name, value: p.revenue }));

  return (
    <div className="dashboard">
      <header className="header">
        <div>
          <h1>ShopSphere Analytics</h1>
          <p>Real-time business analytics across four databases</p>
        </div>
        <button className="live-toggle" onClick={toggleLive}>
          {liveOn ? "Live updates on" : "Live updates off"}
        </button>
        <div className="status">
          <span className={`status-dot ${status === "Connected" ? "online" : "offline"}`} />
          {status}
        </div>
      </header>

      <nav className="tabs" role="tablist">
        {TABS.map((t) => (
          <button key={t} role="tab" aria-selected={tab === t}
            className={`tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </nav>

      <main className="container">
        {tab === "Overview" && (
          <>
            <section className="cards four">
              <div className="card hero">
                <div className="card-title">Revenue</div>
                <div className="card-value">{inr(totalRevenue)}</div>
                <div className="card-subtitle">Running total</div>
              </div>
              <div className="card">
                <div className="card-title">Orders</div>
                <div className="card-value">{totalOrders.toLocaleString("en-IN")}</div>
                <div className="card-subtitle">
                  {perMin === null ? "Measuring rate..." : `${perMin.toFixed(1)} per minute`}
                </div>
              </div>
              <div className="card">
                <div className="card-title">Active users</div>
                <div className="card-value">{activeUsers}</div>
                <div className="card-subtitle">Currently active</div>
              </div>
              <div className="card">
                <div className="card-title">Average order</div>
                <div className="card-value">{inr(aov)}</div>
                <div className="card-subtitle">Revenue ÷ orders</div>
              </div>
            </section>

            <section className="panel">
              <div className="panel-header">
                <div><h2>Live trend</h2><p>Last {liveData.length || 0} updates from the WebSocket</p></div>
                <div className="segmented">
                  {[["orders", "Orders"], ["revenue", "Revenue"], ["users", "Active users"]].map(([k, l]) => (
                    <button key={k} className={metric === k ? "on" : ""} onClick={() => setMetric(k)}>{l}</button>
                  ))}
                </div>
              </div>
              <div className="chart">
                {liveData.length ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={liveData}>
                      <CartesianGrid stroke="#243949" strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="time" {...axis} />
                      <YAxis {...axis} domain={["auto", "auto"]} allowDecimals={false} />
                      <Tooltip {...tip} />
                      <Line type="monotone" dataKey={metric} stroke="#f2b544" strokeWidth={3} dot={false} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : <div className="empty-chart">Waiting for live data. Is the producer running?</div>}
              </div>
            </section>

            <section className="panel">
              <div className="panel-header"><div><h2>Recent orders</h2><p>Latest processed orders</p></div></div>
              <div className="orders">
                {orders.length ? orders.map((o) => (
                  <div className="order" key={o.order_id + o.received_at}>
                    <div><strong>{o.product_name}</strong><small>{o.order_id} · {o.user_id}</small></div>
                    <div className="order-right"><strong>{inr(o.amount)}</strong><span className="placed">{o.status}</span></div>
                  </div>
                )) : <div className="empty">No orders yet</div>}
              </div>
            </section>
          </>
        )}

        {tab === "Products" && (
          <>
            <section className="grid-section">
              <div className="panel">
                <div className="panel-header"><div><h2>Orders by product</h2><p>Best sellers by order count</p></div></div>
                <div className="chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={topProducts} layout="vertical" margin={{ left: 20 }}>
                      <CartesianGrid stroke="#243949" strokeDasharray="3 3" horizontal={false} />
                      <XAxis type="number" {...axis} allowDecimals={false} />
                      <YAxis type="category" dataKey="name" width={95} interval={0} {...axis} />
                      <Tooltip {...tip} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                      <Bar dataKey="orders" fill="#46c8b5" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="panel">
                <div className="panel-header"><div><h2>Revenue share</h2><p>Top 6 products</p></div></div>
                <div className="chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={60} outerRadius={100} paddingAngle={2} stroke="none" isAnimationActive={false}>
                        {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Tooltip {...tip} formatter={(v) => inr(v)} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="legend">
                  {pieData.map((d, i) => (
                    <span key={d.name}><i style={{ background: COLORS[i % COLORS.length] }} />{d.name}</span>
                  ))}
                </div>
              </div>
            </section>

            <section className="grid-section">
              <div className="panel">
                <div className="panel-header"><div><h2>Product ranking</h2><p>Orders and revenue</p></div></div>
                <div className="table-wrapper">
                  <table>
                    <thead><tr><th>Product</th><th>Orders</th><th>Revenue</th></tr></thead>
                    <tbody>
                      {topProducts.map((p) => (
                        <tr key={p.product_id}><td><strong>{p.name}</strong></td><td>{p.orders}</td><td>{inr(p.revenue)}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              <div className="panel">
                <div className="panel-header">
                  <div><h2>Bought together</h2><p>Recommendations from the Neo4j graph</p></div>
                  <select value={recProduct} onChange={(e) => setRecProduct(e.target.value)} aria-label="Product">
                    {topProducts.map((p) => <option key={p.product_id} value={p.product_id}>{p.name}</option>)}
                  </select>
                </div>
                <div className="orders">
                  {recs?.also_bought?.length ? recs.also_bought.map((r) => (
                    <div className="order" key={r.product_id}>
                      <div><strong>{r.name}</strong><small>{r.product_id}</small></div>
                      <span className="placed">{r.strength} shared buyers</span>
                    </div>
                  )) : <div className="empty">No recommendations yet for this product</div>}
                </div>
              </div>
            </section>
          </>
        )}

        {tab === "Behavior" && (
          <section className="panel">
            <div className="panel-header">
              <div><h2>Shopping funnel</h2><p>Page visits from Cassandra: {clicks?.total_clicks ?? 0} clicks{clicks?.truncated ? " (sampled)" : ""}</p></div>
            </div>
            <div className="chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={pages}>
                  <CartesianGrid stroke="#243949" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="page" {...axis} />
                  <YAxis {...axis} allowDecimals={false} />
                  <Tooltip {...tip} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                  <Bar dataKey="clicks" fill="#f2b544" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="funnel">
              {pages.map((p) => (
                <div key={p.page}><strong>{Math.round((p.clicks / homeClicks) * 100)}%</strong><span>{p.page} vs home</span></div>
              ))}
            </div>
          </section>
        )}

        {tab === "System" && (
          <>
            <section className="cards four even">
              {DBS.map((d) => {
                const up = health?.databases?.[d.key] === "up";
                return (
                  <div className="card" key={d.key}>
                    <div className="card-title">{d.name}</div>
                    <div className={`card-value small ${up ? "ok" : "bad"}`}>{health ? (up ? "Up" : "Down") : "Unknown"}</div>
                    <div className="card-subtitle">{d.role}</div>
                  </div>
                );
              })}
            </section>
            <section className="panel">
              <div className="panel-header"><div><h2>Why four databases?</h2><p>Each one handles the data it is best at</p></div></div>
              <div className="flow">Generator → Kafka → Stream processor → MongoDB · Cassandra · Redis · Neo4j → FastAPI → this dashboard</div>
            </section>
          </>
        )}
      </main>

      <footer>ShopSphere • Multi-NoSQL Real-Time Analytics Platform</footer>
    </div>
  );
}
