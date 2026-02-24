import React, { useState } from "react";
import { Form, Input, Button, message, Card } from "antd";
import { useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import "../styles/auth-background.css";
import api from "../api/axios";

interface RegisterFormValues {
    name: string;
    email: string;
    password: string;
}

const Register: React.FC = () => {
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();
    const location = useLocation();

    const inviteToken =
        new URLSearchParams(location.search).get("token") || null;

    const onFinish = async (values: RegisterFormValues) => {
        try {
            setLoading(true);

            await api.post("/users/register", {
                name: values.name,
                email: values.email,
                password: values.password,
                token: inviteToken,
            });

            message.success("Registration successful. Please login.");
            navigate("/login");
        } catch (error: any) {
            message.error(
                error?.response?.data?.detail || "Registration failed"
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
                <Form layout="vertical" onFinish={onFinish}>
                    <Form.Item
                        label="Full Name"
                        name="name"
                        rules={[{ required: true, message: "Name is required" }]}
                    >
                        <Input />
                    </Form.Item>

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