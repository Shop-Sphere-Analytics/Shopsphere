import { useEffect, useRef, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import "./App.css";

const API = "http://localhost:8000";

function App() {
  const [revenue, setRevenue] = useState(null);
  const [activeUsers, setActiveUsers] = useState(null);
  const [topProducts, setTopProducts] = useState([]);
  const [liveUpdates, setLiveUpdates] = useState(true);
  const liveUpdatesRef = useRef(true);

  function toggleLiveUpdates() {
    setLiveUpdates((previous) => { const next = previous ? false : true; liveUpdatesRef.current = next; return next; });
  }
  const [orders, setOrders] = useState([]);
  const [liveData, setLiveData] = useState([]);

  const [apiStatus, setApiStatus] = useState("Checking...");

  useEffect(() => {
    loadDashboard();
    connectWebSocket();
  }, []);

  async function loadDashboard() {
    try {
      const [revenueRes, usersRes, productsRes, ordersRes] =
        await Promise.all([
          fetch(`${API}/api/revenue`),
          fetch(`${API}/api/active-users`),
          fetch(`${API}/api/top-products?limit=5`),
          fetch(`${API}/api/orders?limit=10`),
        ]);

      const revenueData = await revenueRes.json();
      const usersData = await usersRes.json();
      const productsData = await productsRes.json();
      const ordersData = await ordersRes.json();

      setRevenue(revenueData);
      setActiveUsers(usersData.active_users);
      setTopProducts(productsData.top_products);
      setOrders(ordersData.orders);

      setApiStatus("Connected");
    } catch (error) {
      console.error("API error:", error);
      setApiStatus("Backend offline");
    }
  }

  function connectWebSocket() {
    try {
      const socket = new WebSocket("ws://localhost:8000/ws/live-updates");

      socket.onopen = () => {
        console.log("WebSocket connected");
      };

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (liveUpdatesRef.current === false) return;

        if (
          data.revenue_today !== undefined &&
          data.orders_today !== undefined &&
          data.active_users !== undefined
        ) {
          setRevenue((previous) => ({
            ...previous,
            revenue_today: data.revenue_today,
            orders_today: data.orders_today,
          }));

          setActiveUsers(data.active_users);

          setLiveData((previous) => {
            const newPoint = {
              time: new Date().toLocaleTimeString(),
              revenue: data.revenue_today,
              orders: data.orders_today,
              users: data.active_users,
            };

            const updated = [...previous, newPoint];

            return updated.slice(-12);
          });
        }
      };

      socket.onerror = () => {
        console.log("WebSocket connection failed");
      };

      socket.onclose = () => {
        console.log("WebSocket disconnected");
      };
    } catch (error) {
      console.error("WebSocket error:", error);
    }
  }

  return (
    <div className="dashboard">
      <header className="header">
        <div>
          <h1>ShopSphere Analytics</h1>
          <p>Real-Time Business Analytics Dashboard</p>
        </div>

        <button className="live-toggle" onClick={toggleLiveUpdates}>
          {liveUpdates ? "🟢 Live Updates: ON" : "⚪ Live Updates: OFF"}
        </button>

        <div className="status">
          <span
            className={`status-dot ${
              apiStatus === "Connected" ? "online" : "offline"
            }`}
          ></span>
          {apiStatus}
        </div>
      </header>

      <main className="container">
        {/* KPI CARDS */}
        <section className="cards">
          <div className="card">
            <div className="card-title">Revenue</div>
            <div className="card-value">
              ₹
              {revenue?.revenue_today?.toLocaleString("en-IN", {
                minimumFractionDigits: 2,
              }) || "0.00"}
            </div>
            <div className="card-subtitle">Running total</div>
          </div>

          <div className="card">
            <div className="card-title">Orders</div>
            <div className="card-value">
              {revenue?.orders_today?.toLocaleString("en-IN") || "0"}
            </div>
            <div className="card-subtitle">Total orders</div>
          </div>

          <div className="card">
            <div className="card-title">Active Users</div>
            <div className="card-value">
              {activeUsers?.toLocaleString("en-IN") || "0"}
            </div>
            <div className="card-subtitle">Currently active</div>
          </div>
        </section>

        {/* LIVE CHART */}
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Live Activity</h2>
              <p>Real-time updates from WebSocket</p>
            </div>

            <span className="live-badge">● LIVE</span>
          </div>

          <div className="chart">
            {liveData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={liveData}>
                  <CartesianGrid strokeDasharray="3 3" />

                  <XAxis dataKey="time" />

                  <YAxis />

                  <Tooltip />

                  <Line
                    type="monotone"
                    dataKey="orders"
                    strokeWidth={3}
                    name="Orders"
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-chart">
                Waiting for live WebSocket data...
              </div>
            )}
          </div>
        </section>

        {/* LOWER SECTION */}
        <section className="grid-section">
          {/* TOP PRODUCTS */}
          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>Top Products</h2>
                <p>Products by orders and revenue</p>
              </div>
            </div>

            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Orders</th>
                    <th>Revenue</th>
                  </tr>
                </thead>

                <tbody>
                  {topProducts.length > 0 ? (
                    topProducts.map((product, index) => (
                      <tr key={product.product_id || index}>
                        <td>
                          <strong>{product.name}</strong>
                        </td>
                        <td>{product.orders}</td>
                        <td>
                          ₹
                          {Number(product.revenue || 0).toLocaleString(
                            "en-IN",
                            {
                              minimumFractionDigits: 2,
                            }
                          )}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="3" className="empty">
                        No product data available
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* RECENT ORDERS */}
          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>Recent Orders</h2>
                <p>Latest processed orders</p>
              </div>
            </div>

            <div className="orders">
              {orders.length > 0 ? (
                orders.slice(0, 6).map((order, index) => (
                  <div className="order" key={order.order_id || index}>
                    <div>
                      <strong>{order.product_name}</strong>
                      <small>{order.order_id}</small>
                    </div>

                    <div className="order-right">
                      <strong>
                        ₹
                        {Number(order.amount || 0).toLocaleString("en-IN", {
                          minimumFractionDigits: 2,
                        })}
                      </strong>

                      <span className="placed">
                        {order.status || "placed"}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="empty">No orders available</div>
              )}
            </div>
          </div>
        </section>
      </main>

      <footer>
        ShopSphere • Multi-NoSQL Real-Time Analytics Platform
      </footer>
    </div>
  );
}

export default App;
