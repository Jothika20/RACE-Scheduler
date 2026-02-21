import React, { useEffect, useState } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin, { DateClickArg } from '@fullcalendar/interaction';
import {
    Modal,
    Form,
    Input,
    DatePicker,
    TimePicker,
    Button,
    Select,
    Checkbox, // ✅ ADDED THIS
    App
} from 'antd';
import moment from 'moment';
import api from '../api/axios';
import axios from 'axios';
import { hasPermission } from '../utils/permissions';
import listPlugin from '@fullcalendar/list';
import './Dashboard.css';
import ProfileModal from '../components/ProfileModal';
import { getErrorMessage } from '../utils/error';

const { Option } = Select;

const Dashboard: React.FC = () => {
    const { message } = App.useApp();
    const [events, setEvents] = useState<any[]>([]);
    const [isEventModalOpen, setIsEventModalOpen] = useState(false);
    const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
    const [form] = Form.useForm();
    const [inviteForm] = Form.useForm();
    const [userOptions, setUserOptions] = useState<any[]>([]);
    const [formError, setFormError] = useState<string | null>(null);
    const [startDate, setStartDate] = useState<any>(null);
    const [currentUser, setCurrentUser] = useState<any>(null);
    const [hasLoadedUsers, setHasLoadedUsers] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [calendarView, setCalendarView] = useState('timeGridWeek');
    const [isPreviewOpen, setIsPreviewOpen] = useState(false);
    const [isEditMode, setIsEditMode] = useState(false);
    const [selectedEvent, setSelectedEvent] = useState<any>(null);
    const [isProfileOpen, setIsProfileOpen] = useState(false);

    // Recurrence State
    const [isRecurring, setIsRecurring] = useState(false);
    const [recurrenceType, setRecurrenceType] = useState('daily');

    const token = localStorage.getItem('token');

    // ─────────── FETCH CURRENT USER ─────────── //
    useEffect(() => {
        const fetchUser = async () => {
            try {
                const res = await api.get('/users/me');
                setCurrentUser(res.data);
            } catch (error: any) {
                console.error("Fetch user error:", error);
                // Don't show error for 401 as interceptor handles it, or if just not logged in yet
                if (error?.response?.status !== 401) {
                    message.error(getErrorMessage(error));
                }
            }
        };
        fetchUser();
    }, []);

    // ─────────── FETCH EVENTS ───────────
    const fetchEvents = async () => {
        try {
            const res = await api.get('/events/');
            const mapped = res.data.map((e: any) => ({
                id: e.id,
                title: e.title,
                start: e.start_time,
                end: e.end_time,
                extendedProps: {
                    status: e.status,
                    participants: e.participants,
                    event_type: e.event_type,
                },
                classNames: [
                    e.status === 'cancelled' ? 'cancelled-event' : '',
                    ['holiday', 'weekly_off', 'announced_holiday'].includes(e.event_type) ? 'holiday-event' : '',
                    e.event_type === 'combined' ? 'combined-event' : '',
                ],
            }));
            setEvents(mapped);
        } catch (error: any) {
            console.error("Fetch events error:", error);
            message.error(getErrorMessage(error));
        }
    };

    useEffect(() => {
        fetchEvents();
    }, []);

    // ─────────── FETCH USERS ─────────── //
    const fetchUsers = async () => {
        if (hasLoadedUsers) return;
        try {
            const res = await api.get('/users');
            setUserOptions(
                res.data.map((u: any) => ({
                    label: u.name,
                    value: u.id,
                }))
            );
            setHasLoadedUsers(true);
        } catch {
            console.error('Failed to fetch users');
        }
    };

    // ─────────── EVENT CREATION ─────────── //
    const onDateClick = (arg: DateClickArg) => {
        if (!currentUser) return;

        if (!hasPermission(currentUser?.permissions, 'can_create_events'))
            return;

        const clickedDate = moment(arg.date);

        // 🚫 Block holiday scheduling in UI
        const isHoliday = events.some(
            (e: any) =>
                e.extendedProps?.event_type === 'holiday' &&
                moment(e.start).isSame(clickedDate, 'day')
        );

        if (isHoliday) {
            message.error("Cannot create regular events on holidays");
            return;
        }

        setIsEditMode(false);
        setSelectedEvent(null);
        form.resetFields();

        // Use the clicked date as the base for time values
        const startTimeWithDate = clickedDate.clone().set({ hour: 10, minute: 0, second: 0, millisecond: 0 });
        const endTimeWithDate = clickedDate.clone().set({ hour: 10, minute: 30, second: 0, millisecond: 0 });

        form.setFieldsValue({
            date: clickedDate.clone().startOf('day'), // Just the date part
            start: startTimeWithDate, // Full datetime, but we'll extract time in submission
            end: endTimeWithDate, // Full datetime, but we'll extract time in submission
            event_type: "regular",
            is_recurring: false,
            recurrence_type: "daily",
            recurrence_end_date: clickedDate.clone().add(1, 'week'),
            recurrence_days: []
        });

        setIsRecurring(false);
        setRecurrenceType('daily');

        setIsEventModalOpen(true);
    };

    // ─────────── SUBMIT EVENT ───────────
    const onEventFinish = async (values: any) => {
        console.log("===== onEventFinish called =====");
        console.log("Form values:", values);
        console.log("Start value type:", typeof values.start, values.start);
        console.log("End value type:", typeof values.end, values.end);

        if (submitting) return;
        setSubmitting(true);

        try {
            setFormError(null);

            // Get date and time components from form
            // Ensure we have moment objects (AntD 5 returns Dayjs)
            const dateValue = values.date ? moment(values.date.toDate()) : null;
            const startTime = values.start ? moment(values.start.toDate()) : null;
            const endTime = values.end ? moment(values.end.toDate()) : null;

            console.log("dateValue (Moment):", dateValue, "isValid:", dateValue?.isValid());
            console.log("startTime (Moment):", startTime, "isValid:", startTime?.isValid());
            console.log("endTime (Moment):", endTime, "isValid:", endTime?.isValid());

            // Validate that we have valid moment objects
            if (!dateValue || !dateValue.isValid()) {
                message.error("Please select a date");
                return;
            }

            if (!startTime || !startTime.isValid()) {
                message.error("Please select a start time");
                return;
            }

            if (!endTime || !endTime.isValid()) {
                message.error("Please select an end time");
                return;
            }

            // Extract just the time components from the time pickers
            const startHour = startTime.hour();
            const startMinute = startTime.minute();
            const endHour = endTime.hour();
            const endMinute = endTime.minute();

            console.log(`Extracted times - Start: ${startHour}:${startMinute}, End: ${endHour}:${endMinute}`);

            // Create new moment objects for start and end by cloning the date and setting the time
            const start = dateValue.clone().set({
                hour: startHour,
                minute: startMinute,
                second: 0,
                millisecond: 0
            });

            const end = dateValue.clone().set({
                hour: endHour,
                minute: endMinute,
                second: 0,
                millisecond: 0
            });

            console.log("Start datetime:", start.format());
            console.log("End datetime:", end.format());
            console.log("Start ISO:", start.toISOString());
            console.log("End ISO:", end.toISOString());

            // Only check for past dates when creating new events, not when editing
            if (!isEditMode && start.isBefore(moment())) {
                message.error("Cannot schedule events in the past");
                return;
            }

            if (!end.isAfter(start)) {
                message.error("End time must be after start time");
                return;
            }

            // Handle recurrence end date (convert Dayjs to ISO if present)
            let recurrenceEndISO = null;
            if (values.is_recurring && values.recurrence_end_date) {
                // Check if it's Dayjs (from AntD) or Moment
                // If it has .toDate(), use it
                try {
                    recurrenceEndISO = values.recurrence_end_date.toDate().toISOString();
                } catch (e) {
                    // Fallback/Safety
                    recurrenceEndISO = moment(values.recurrence_end_date).toISOString();
                }
            }

            const payload = {
                title: values.title,
                start_time: start.toISOString(),
                end_time: end.toISOString(),
                participants: values.participants || [],
                event_type: values.event_type || "regular",
                // Recurrence
                recurrence_type: values.is_recurring ? values.recurrence_type : null,
                recurrence_end_date: recurrenceEndISO,
                recurrence_days: values.is_recurring && values.recurrence_type === 'weekly' ? values.recurrence_days : [],
            };

            console.log("Payload:", payload);

            if (isEditMode && selectedEvent && selectedEvent.id) {
                const eventId = parseInt(selectedEvent.id);
                await api.put(`/events/${eventId}`, payload);
                message.success("Event updated successfully!");
            } else {
                await api.post('/events/', payload);
                message.success("Event added successfully!");
            }

            setIsEventModalOpen(false);
            setIsEditMode(false);
            setSelectedEvent(null);
            form.resetFields();
            fetchEvents();

        } catch (err: any) {
            console.error("Error:", err);
            const apiMsg = getErrorMessage(err);
            setFormError(apiMsg);
            message.error(apiMsg);
        } finally {
            setSubmitting(false);
        }
    };

    const handleEventModalClose = () => {
        setIsEventModalOpen(false);
        form.resetFields();
        setFormError(null);
        setStartDate(null);
        setIsEditMode(false);
        setSelectedEvent(null);
    };

    const onInviteFinish = async (values: any) => {
        try {
            await api.post('/users/invite-user', values);
            message.success('User invited successfully!');
            setIsInviteModalOpen(false);
            inviteForm.resetFields();
        } catch (error: any) {
            message.error(getErrorMessage(error));
        }
    };

    // Populate form when opening in edit mode
    // In your useEffect that populates the form
    useEffect(() => {
        if (isEventModalOpen && isEditMode && selectedEvent) {
            console.log("Populating form with selectedEvent:", selectedEvent);

            // Get the raw event data
            const eventData = selectedEvent.rawData || selectedEvent;

            // Create moment objects from the event data
            const startMoment = moment(eventData.start);
            const endMoment = moment(eventData.end);

            // Create time values using the start date as reference so TimePicker works correctly
            const startTimeWithDate = startMoment.clone().set({
                hour: startMoment.hour(),
                minute: startMoment.minute(),
                second: 0,
                millisecond: 0
            });

            const endTimeWithDate = startMoment.clone().set({
                hour: endMoment.hour(),
                minute: endMoment.minute(),
                second: 0,
                millisecond: 0
            });

            // Set form values
            form.setFieldsValue({
                title: eventData.title,
                date: startMoment.clone().startOf('day'), // Just the date part
                start: startTimeWithDate, // Full datetime for TimePicker
                end: endTimeWithDate, // Full datetime for TimePicker
                participants: eventData.extendedProps?.participants?.map(
                    (p: any) => p.id
                ),
                event_type: eventData.extendedProps?.event_type || "regular"
            });

            console.log("Set form values - start time:", startTimeWithDate.format("HH:mm"), "end time:", endTimeWithDate.format("HH:mm"));
        }
    }, [isEventModalOpen, isEditMode, selectedEvent, form]);

    // ─────────── UI ─────────── //
    return (
        <div style={{ padding: '20px' }}>
            {/* Header Section */}
            <div
                className='dashboard-header'
                style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '10px',
                }}
            >
                <div>
                    <h2 style={{ margin: 0 }}>RACE Scheduler</h2>
                    <div style={{ fontSize: '13px', color: '#6b7280' }}>
                        Team scheduling & availability management
                    </div>
                </div>
                <div style={{ display: 'flex', gap: '10px' }}>
                    {/* 👇 Calendar View Filter */}
                    <Select
                        value={calendarView}
                        onChange={(value) => setCalendarView(value)}
                        style={{ width: 150 }}
                    >
                        <Option value="dayGridDay">Day</Option>
                        <Option value="timeGridWeek">Week</Option>
                        <Option value="dayGridMonth">Month</Option>
                        <Option value="listYear">Year (Agenda)</Option>
                    </Select>

                    {hasPermission(currentUser?.permissions, 'can_create_users') && (
                        <Button
                            type="primary"
                            onClick={() => setIsInviteModalOpen(true)}
                        >
                            Invite User
                        </Button>
                    )}
                    <Button onClick={() => setIsProfileOpen(true)}>
                        My Profile
                    </Button>
                    <Button
                        className="logout-btn"
                        onClick={() => {
                            localStorage.removeItem('token');
                            window.location.href = '/login';
                        }}
                    >
                        Logout
                    </Button>
                </div>
            </div>

            {/* Calendar */}
            <div className="calendar-glass-wrapper">
                <FullCalendar
                    plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin, listPlugin]}
                    initialView={calendarView}
                    events={events}
                    dateClick={onDateClick}
                    height="auto"
                    key={calendarView}

                    /* ✅ SHOW FULL 24 HOURS */
                    allDaySlot={false}

                    /* ✅ TEAMS-LIKE TIME GRID */
                    slotDuration="00:30:00"      // 30-minute slots
                    snapDuration="00:30:00"
                    slotLabelInterval="01:00"    // Hour labels only

                    slotLabelFormat={{
                        hour: 'numeric',
                        minute: '2-digit',
                        hour12: true,
                    }}

                    headerToolbar={false}
                    dayMaxEvents={true}
                    eventDisplay="block"

                    eventClick={(info) => {
                        // Find the raw event data from your events array
                        const rawEvent = events.find(e => e.id === info.event.id);

                        // Create a combined object with both calendar event and raw data
                        const eventWithRaw = {
                            ...info.event,
                            rawData: rawEvent,
                            id: info.event.id,
                            title: info.event.title,
                            start: info.event.start,
                            end: info.event.end,
                            extendedProps: info.event.extendedProps
                        };

                        setSelectedEvent(eventWithRaw);
                        setIsPreviewOpen(true);
                    }}
                />
            </div>

            <Modal
                title="Event Details"
                open={isPreviewOpen}
                onCancel={() => {
                    setIsPreviewOpen(false);
                    setSelectedEvent(null);
                    setIsEditMode(false);
                }}
                footer={null}
            >
                {selectedEvent && (
                    <>
                        <p><strong>Title:</strong> {selectedEvent.title}</p>
                        <p>
                            <strong>Time:</strong>{' '}
                            {moment(selectedEvent.start).format('DD MMM YYYY, HH:mm')} –{' '}
                            {moment(selectedEvent.end).format('HH:mm')}
                        </p>
                        <p>
                            <strong>Status:</strong>{' '}
                            {selectedEvent.extendedProps?.status}
                        </p>

                        <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
                            {selectedEvent.extendedProps?.status !== 'cancelled' && (
                                <>
                                    {selectedEvent.extendedProps?.status === 'active' && (
                                        <Button
                                            onClick={() => {
                                                setIsEditMode(true);
                                                setIsPreviewOpen(false);
                                                setIsEventModalOpen(true);
                                                // Form will be populated by the useEffect
                                            }}
                                        >
                                            Edit
                                        </Button>
                                    )}

                                    <Button
                                        danger
                                        onClick={async () => {
                                            try {
                                                await api.delete(`/events/${selectedEvent.id}`);
                                                message.success('Event cancelled');
                                                setIsPreviewOpen(false);
                                                fetchEvents();
                                            } catch (error: any) {
                                                message.error(getErrorMessage(error));
                                            }
                                        }}
                                    >
                                        Cancel Event
                                    </Button>
                                </>
                            )}
                        </div>
                    </>
                )}
            </Modal>

            {/* ─────────── ADD/EDIT EVENT MODAL ─────────── */}
            <Modal
                title={isEditMode ? "Edit Event" : "Add Event"}
                open={isEventModalOpen}
                onCancel={handleEventModalClose}
                footer={null}
            >
                <Form
                    form={form}
                    onFinish={onEventFinish}
                    layout="vertical"
                    className="dashboard-form"
                    onValuesChange={(changedValues) => {
                        if (changedValues.is_recurring !== undefined) {
                            setIsRecurring(changedValues.is_recurring);
                        }
                        if (changedValues.recurrence_type !== undefined) {
                            setRecurrenceType(changedValues.recurrence_type);
                        }
                    }}
                >
                    {formError && (
                        <div style={{ color: 'red', marginBottom: '10px' }}>{formError}</div>
                    )}
                    <Form.Item
                        label="Event Title"
                        name="title"
                        rules={[{ required: true }]}
                    >
                        <Input />
                    </Form.Item>

                    {/* ✅ EVENT TYPE */}
                    <Form.Item
                        label="Event Type"
                        name="event_type"
                        initialValue="regular"
                    >
                        <Select>
                            <Option value="regular">Regular</Option>
                            <Option value="combined">Combined Batch</Option>

                            {(currentUser?.role === 'admin' ||
                                currentUser?.role === 'super_admin') && (
                                    <>
                                        <Option value="holiday">Holiday</Option>
                                        <Option value="weekly_off">Weekly Off</Option>
                                        <Option value="announced_holiday">
                                            Announced Holiday
                                        </Option>
                                    </>
                                )}
                        </Select>
                    </Form.Item>

                    <Form.Item
                        label="Date"
                        name="date"
                        rules={[{ required: true }]}
                    >
                        <DatePicker
                            style={{ width: '100%' }}
                            disabledDate={(current) =>
                                current && current < moment().startOf('day')
                            }
                        />
                    </Form.Item>

                    <Form.Item name="participants" label="Invite Users">
                        <Select
                            mode="multiple"
                            options={userOptions}
                            placeholder="Select participants"
                            onFocus={fetchUsers}
                        />
                    </Form.Item>

                    {/* 30-minute enforced */}
                    <Form.Item label="Start Time" name="start" rules={[{ required: true }]}>
                        <TimePicker
                            format="HH:mm"
                            minuteStep={30}
                            hideDisabledOptions
                            disabledTime={() => ({
                                disabledMinutes: () =>
                                    Array.from({ length: 60 }, (_, i) => i)
                                        .filter(m => m !== 0 && m !== 30)
                            })}
                        />
                    </Form.Item>

                    <Form.Item label="End Time" name="end" rules={[{ required: true }]}>
                        <TimePicker
                            format="HH:mm"
                            minuteStep={30}
                            hideDisabledOptions
                            disabledTime={() => ({
                                disabledMinutes: () =>
                                    Array.from({ length: 60 }, (_, i) => i)
                                        .filter(m => m !== 0 && m !== 30)
                            })}
                        />
                    </Form.Item>

                    {/* RECURRENCE SECTION */}
                    <Form.Item name="is_recurring" valuePropName="checked">
                        <Checkbox>Repeat Event</Checkbox>
                    </Form.Item>

                    {isRecurring && (
                        <div style={{ border: '1px solid #eee', padding: '10px', borderRadius: '4px', marginBottom: '15px' }}>
                            <div style={{ display: 'flex', gap: '10px' }}>
                                <Form.Item
                                    label="Recurrence Type"
                                    name="recurrence_type"
                                    style={{ flex: 1 }}
                                    rules={[{ required: true, message: 'Select type' }]}
                                >
                                    <Select>
                                        <Option value="daily">Daily</Option>
                                        <Option value="weekly">Weekly</Option>
                                    </Select>
                                </Form.Item>

                                <Form.Item
                                    label="End Date"
                                    name="recurrence_end_date"
                                    style={{ flex: 1 }}
                                    rules={[{ required: true, message: 'Select end date' }]}
                                >
                                    <DatePicker
                                        style={{ width: '100%' }}
                                        disabledDate={(current) =>
                                            current && current < moment().startOf('day')
                                        }
                                    />
                                </Form.Item>
                            </div>

                            {recurrenceType === 'weekly' && (
                                <Form.Item
                                    label="Repeat On"
                                    name="recurrence_days"
                                    rules={[{ required: true, message: 'Select at least one day' }]}
                                >
                                    <Checkbox.Group options={[
                                        'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
                                    ]} />
                                </Form.Item>
                            )}
                        </div>
                    )}

                    <Button type="primary" htmlType="submit" block loading={submitting}>
                        {isEditMode ? "Update Event" : "Add Event"}
                    </Button>

                </Form>
            </Modal>

            {/* ─────────── INVITE USER MODAL ─────────── */}
            <Modal
                title="Invite User"
                open={isInviteModalOpen}
                onCancel={() => setIsInviteModalOpen(false)}
                footer={null}
            >
                <Form form={inviteForm} onFinish={onInviteFinish} layout="vertical">
                    <Form.Item
                        label="Email"
                        name="email"
                        rules={[{ required: true, type: 'email' }]}
                    >
                        <Input />
                    </Form.Item>

                    <Form.Item
                        label="Role"
                        name="role"
                        rules={[{ required: true, message: 'Please select a role' }]}
                    >
                        <Select placeholder="Select role">
                            {hasPermission(currentUser?.permissions, 'can_create_users') && (
                                <Option value="user">User</Option>
                            )}
                            {hasPermission(currentUser?.permissions, 'can_manage_roles') && (
                                <Option value="admin">Admin</Option>
                            )}
                            {hasPermission(currentUser?.permissions, 'can_manage_roles') && (
                                <Option value="super_admin">Super Admin</Option>
                            )}
                        </Select>
                    </Form.Item>

                    <Form.Item>
                        <Button type="primary" htmlType="submit" block>
                            Send Invite
                        </Button>
                    </Form.Item>
                </Form>
            </Modal>
            <ProfileModal
                open={isProfileOpen}
                onClose={() => setIsProfileOpen(false)}
                currentUser={currentUser}
                onUpdated={(u) => setCurrentUser(u)}
            />
        </div>
    );
};

export default Dashboard;