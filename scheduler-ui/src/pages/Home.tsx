import { Button } from "antd";
import { useNavigate } from "react-router-dom";
import "../styles/auth-background.css";

const Home = () => {
    const navigate = useNavigate();

    return (
        <div className="auth-container" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-evenly' }}>
            <div className="auth-card" style={{ maxWidth: 520, textAlign: "center" }}>
                <h1 className="login-title">Race Scheduler</h1>

                <p style={{ opacity: 0.85, marginBottom: 32 }}>
                    Plan races, manage events, and collaborate efficiently across teams.
                </p>

                <Button
                    type="primary"
                    size="large"
                    block
                    onClick={() => navigate("/login")}
                >
                    Login
                </Button>

                <Button
                    size="large"
                    block
                    style={{ marginTop: 12 }}
                    onClick={() => navigate("/register")}
                >
                    Register
                </Button>
            </div>
            <div style={{ color: "#fff" }}>
                © 2026 RACE. All Rights Reserved.
            </div>
        </div>
    );
};

export default Home;
