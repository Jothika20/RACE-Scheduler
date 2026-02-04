import React, { useState } from "react";
import { Form, Input, Button, message, Card } from "antd";
import { useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import "../styles/auth-background.css";

interface RegisterFormValues {
    name: string;
    email?: string;
    mobile?: string;
    password: string;
}

const Register: React.FC = () => {
    const [loading, setLoading] = useState(false);
    const [registerMethod, setRegisterMethod] = useState<"email" | "mobile">("email");

    const navigate = useNavigate();
    const location = useLocation();

    const inviteToken =
        new URLSearchParams(location.search).get("token") || null;

    const onFinish = async (values: RegisterFormValues) => {
        try {
            setLoading(true);

            if (!values.email && !values.mobile) {
                message.error("Email or Mobile number is required");
                return;
            }

            await axios.post("http://localhost:8000/users/register", {
                name: values.name,
                email: values.email ?? null,
                mobile: values.mobile ?? null,
                password: values.password,
                token: inviteToken,
            });

            message.success("Registration successful. Please login.");
            navigate("/login");
        } catch (error: any) {
            message.error(
                error?.response?.data?.message || "Registration failed"
            );
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-container">
            <Card
                title="Create Account"
                className="auth-card"
                headStyle={{
                    color: "#fff",
                    borderBottom: "1px solid rgba(255,255,255,0.1)",
                }}
            >
                {/* Email / Mobile Toggle */}
                <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
                    <Button
                        block
                        type={registerMethod === "email" ? "primary" : "default"}
                        onClick={() => setRegisterMethod("email")}
                    >
                        Email
                    </Button>
                    <Button
                        block
                        type={registerMethod === "mobile" ? "primary" : "default"}
                        onClick={() => setRegisterMethod("mobile")}
                    >
                        Mobile
                    </Button>
                </div>

                <Form layout="vertical" onFinish={onFinish}>
                    <Form.Item
                        label="Full Name"
                        name="name"
                        rules={[{ required: true, message: "Name is required" }]}
                    >
                        <Input />
                    </Form.Item>

                    {registerMethod === "email" && (
                        <Form.Item
                            label="Email Address"
                            name="email"
                            rules={[
                                { required: true, message: "Email is required" },
                                { type: "email", message: "Enter a valid email" },
                            ]}
                        >
                            <Input />
                        </Form.Item>
                    )}

                    {registerMethod === "mobile" && (
                        <Form.Item
                            label="Mobile Number"
                            name="mobile"
                            rules={[
                                { required: true, message: "Mobile number is required" },
                                {
                                    pattern: /^[0-9]{10}$/,
                                    message: "Enter valid 10-digit mobile number",
                                },
                            ]}
                        >
                            <Input />
                        </Form.Item>
                    )}

                    <Form.Item
                        label="Password"
                        name="password"
                        rules={[
                            { required: true, message: "Password is required" },
                            { min: 6, message: "Minimum 6 characters" },
                        ]}
                    >
                        <Input.Password />
                    </Form.Item>

                    <Button
                        type="primary"
                        htmlType="submit"
                        block
                        loading={loading}
                    >
                        Register
                    </Button>

                    <Button
                        type="link"
                        block
                        style={{ marginTop: 12 }}
                        onClick={() => navigate("/login")}
                    >
                        Already have an account? Login
                    </Button>
                </Form>
            </Card>
        </div>
    );
};

export default Register;
