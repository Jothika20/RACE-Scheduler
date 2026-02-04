import React, { useEffect } from 'react';
import { Modal, Form, Input, Button, message } from 'antd';
import api from '../api/axios';

interface Props {
    open: boolean;
    onClose: () => void;
    currentUser: any;
    onUpdated: (user: any) => void;
}

const ProfileModal: React.FC<Props> = ({
    open,
    onClose,
    currentUser,
    onUpdated,
}) => {
    const [form] = Form.useForm();

    useEffect(() => {
        if (currentUser) {
            form.setFieldsValue({
                name: currentUser.name,
                email: currentUser.email,
                mobile: currentUser.mobile,
            });
        }
    }, [currentUser, form]);

    const onFinish = async (values: any) => {
        if (!values.email && !values.mobile) {
            message.error('Either email or mobile is required');
            return;
        }

        try {
            const res = await api.put('/users/me', values);
            message.success('Profile updated');
            onUpdated(res.data);
            onClose();
        } catch (err: any) {
            message.error(err?.response?.data?.detail || 'Update failed');
        }
    };

    return (
        <Modal
            title="My Profile"
            open={open}
            onCancel={onClose}
            footer={null}
        >
            <Form form={form} layout="vertical" onFinish={onFinish}>
                <Form.Item
                    label="Full Name"
                    name="name"
                    rules={[{ required: true }]}
                >
                    <Input />
                </Form.Item>

                <Form.Item label="Email" name="email">
                    <Input />
                </Form.Item>

                <Form.Item label="Mobile" name="mobile">
                    <Input />
                </Form.Item>

                <Form.Item>
                    <Button type="primary" htmlType="submit" block>
                        Update Profile
                    </Button>
                </Form.Item>
            </Form>
        </Modal>
    );
};

export default ProfileModal;
