import { Form, Input, Button, message } from "antd";
import axios from "axios";
import { useNavigate, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import "../styles/auth-background.css";

interface RegisterFormValues {
    name: string;
    email: string;
    password: string;
}

const Register = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const [inviteToken, setInviteToken] = useState("");

    useEffect(() => {
        const params = new URLSearchParams(location.search);
        const token = params.get("token");
        if (token) setInviteToken(token);
    }, [location.search]);

    const onFinish = async (values: RegisterFormValues) => {
        try {
            const payload = { ...values, token: inviteToken };
            await axios.post("http://localhost:8000/users/register", payload);
            message.success("Account created successfully");
            navigate("/login");
        } catch {
            message.error("Registration failed");
        }
    };

    return (
        <div className="auth-container">
            <div className="auth-card">
                <h2 className="login-title">Create Account</h2>

                <Form layout="vertical" onFinish={onFinish}>
                    <Form.Item label={<span style={{ color: "#fff" }}>Full Name</span>} name="name" rules={[{ required: true }]}>
                        <Input />
                    </Form.Item>

                    {!inviteToken && (
                        <Form.Item
                            label={<span style={{ color: "#fff" }}>Email Address</span>}
                            name="email"
                            rules={[{ required: true, type: "email" }]}
                        >
                            <Input />
                        </Form.Item>
                    )}

                    <Form.Item
                        label={<span style={{ color: "#fff" }}>Password</span>}
                        name="password"
                        rules={[{ required: true }]}
                        hasFeedback
                    >
                        <Input.Password />
                    </Form.Item>

                    <Button type="primary" htmlType="submit" block>
                        Register
                    </Button>

                    <Button
                        type="link"
                        block
                        onClick={() => navigate("/login")}
                        style={{ marginTop: 12, color: '#fff' }}
                    >
                        Already have an account? Login
                    </Button>
                </Form>
            </div>
        </div>
    );
};

export default Register;
