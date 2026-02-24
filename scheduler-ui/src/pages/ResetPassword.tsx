import { useState, useEffect } from 'react';
import { Form, Input, Button, Card, App, Spin, Alert } from 'antd';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import './Login.css';
import { getErrorMessage } from '../utils/error';

const ResetPassword = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const [loading, setLoading] = useState(false);
    const [submitted, setSubmitted] = useState(false);
    const { message } = App.useApp();
    const token = searchParams.get('token');

    useEffect(() => {
        if (!token) {
            message.error('Invalid reset link');
            navigate('/forgot-password');
        }
    }, [token, navigate, message]);

    const onFinish = async (values: any) => {
        if (values.password !== values.confirmPassword) {
            message.error('Passwords do not match');
            return;
        }

        try {
            setLoading(true);
            await axios.post('http://localhost:8000/users/reset-password', {
                token: token,
                new_password: values.password,
            });
            message.success('Password reset successfully!');
            setSubmitted(true);

            // Redirect to login after 2 seconds
            setTimeout(() => {
                navigate('/login');
            }, 2000);
        } catch (err: any) {
            message.error(getErrorMessage(err));
        } finally {
            setLoading(false);
        }
    };

    if (!token) {
        return null;
    }

    return (
        <div className="login-container">
            {loading && (
                <div className="spinner-overlay">
                    <Spin
                        indicator={
                            <img
                                src="/images/reva-spinner.webp"
                                alt="Loading..."
                                className="reva-spinner"
                                style={{ width: '150px', height: '150px' }}
                            />
                        }
                    />
                </div>
            )}

            <Card className="login-card" bordered={false}>
                <h2 className="login-title">Create New Password</h2>

                {submitted ? (
                    <div style={{ textAlign: 'center', padding: '20px' }}>
                        <Alert
                            message="Success"
                            description="Your password has been reset successfully. Redirecting to login..."
                            type="success"
                            showIcon
                            style={{ marginBottom: '20px' }}
                        />
                    </div>
                ) : (
                    <Form onFinish={onFinish} layout="vertical">
                        <Form.Item
                            label={<span className="form-label">New Password</span>}
                            name="password"
                            rules={[
                                {
                                    required: true,
                                    message: 'Please enter a new password'
                                },
                                {
                                    min: 6,
                                    message: 'Password must be at least 6 characters'
                                }
                            ]}
                        >
                            <Input.Password placeholder="Enter new password" />
                        </Form.Item>

                        <Form.Item
                            label={<span className="form-label">Confirm Password</span>}
                            name="confirmPassword"
                            rules={[
                                {
                                    required: true,
                                    message: 'Please confirm your password'
                                }
                            ]}
                        >
                            <Input.Password placeholder="Confirm password" />
                        </Form.Item>

                        <Form.Item>
                            <Button type="primary" htmlType="submit" block>
                                Reset Password
                            </Button>
                        </Form.Item>
                    </Form>
                )}
            </Card>
        </div>
    );
};

export default ResetPassword;
