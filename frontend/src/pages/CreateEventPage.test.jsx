import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext';
import CreateEventPage from './CreateEventPage';
import { aiApi } from '../services/api';

vi.mock('../services/api', () => ({
  aiApi: {
    extractEvent: vi.fn(),
  },
}));

const mockUser = { id: 1, email: 'org@example.com', role: 'ORGANIZER' };
const mockToken = 'fake-token';

const wrapWithProviders = (component) => (
  <AuthProvider>
    <MemoryRouter>
      {component}
    </MemoryRouter>
  </AuthProvider>
);

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem('caep_user', JSON.stringify(mockUser));
  localStorage.setItem('caep_token', mockToken);
});

afterEach(() => {
  localStorage.clear();
});

describe('CreateEventPage AI extraction description mapping', () => {
  test('A non-empty API description populates the description form field', async () => {
    (aiApi.extractEvent).mockResolvedValue({
      extracted_data: {
        title: 'AI Seminar',
        description: 'This seminar covers neural networks, transformer architectures, and practical machine learning applications.',
        category: 'Seminar',
        venue: 'Main Auditorium',
        date: '2027-03-15',
        start_time: '10:00',
        end_time: '12:00',
        tags: [],
      },
      warnings: [],
      confidence: 0.9,
      processing_time_ms: 100,
    });

    render(wrapWithProviders(<CreateEventPage />));

    const announcement = screen.getByPlaceholderText(/Paste event announcement text/i);
    fireEvent.change(announcement, { target: { value: 'Some announcement text' } });

    const extractButton = screen.getByRole('button', { name: /Extract Event Details/i });
    fireEvent.click(extractButton);

    await waitFor(() => {
      expect(aiApi.extractEvent).toHaveBeenCalled();
    });

    const descriptionField = screen.getByLabelText(/Description/i);
    expect(descriptionField).toHaveValue(
      'This seminar covers neural networks, transformer architectures, and practical machine learning applications.'
    );
  });

  test('A provider response using details is normalized to description', async () => {
    (aiApi.extractEvent).mockResolvedValue({
      extracted_data: {
        title: 'AI Workshop',
        details: 'Learn about neural networks and ML.',
        category: 'Workshop',
        venue: 'Lab 204',
        date: '2026-10-20',
        start_time: '09:00',
        end_time: '12:00',
        tags: [],
      },
      warnings: [],
      confidence: 0.85,
      processing_time_ms: 100,
    });

    render(wrapWithProviders(<CreateEventPage />));

    const announcement = screen.getByPlaceholderText(/Paste event announcement text/i);
    fireEvent.change(announcement, { target: { value: 'Some announcement text' } });

    const extractButton = screen.getByRole('button', { name: /Extract Event Details/i });
    fireEvent.click(extractButton);

    await waitFor(() => {
      expect(aiApi.extractEvent).toHaveBeenCalled();
    });

    const descriptionField = screen.getByLabelText(/Description/i);
    expect(descriptionField).toHaveValue('Learn about neural networks and ML.');
  });

  test('An absent description does not erase an existing manually entered description', async () => {
    (aiApi.extractEvent).mockResolvedValue({
      extracted_data: {
        title: 'AI Seminar',
        category: 'Seminar',
        venue: 'Main Auditorium',
        date: '2027-03-15',
        start_time: '10:00',
        end_time: '12:00',
        tags: [],
      },
      warnings: [],
      confidence: 0.8,
      processing_time_ms: 100,
    });

    render(wrapWithProviders(<CreateEventPage />));

    const descriptionField = screen.getByLabelText(/Description/i);
    const manualDescription = 'Manually entered description text.';
    fireEvent.change(descriptionField, { target: { value: manualDescription } });
    expect(descriptionField).toHaveValue(manualDescription);

    const announcement = screen.getByPlaceholderText(/Paste event announcement text/i);
    fireEvent.change(announcement, { target: { value: 'Some announcement text' } });

    const extractButton = screen.getByRole('button', { name: /Extract Event Details/i });
    fireEvent.click(extractButton);

    await waitFor(() => {
      expect(aiApi.extractEvent).toHaveBeenCalled();
    });

    expect(descriptionField).toHaveValue(manualDescription);
  });

  test('Other extracted fields continue to populate correctly', async () => {
    (aiApi.extractEvent).mockResolvedValue({
      extracted_data: {
        title: 'AI Hackathon 2026',
        description: 'Join 500+ students in a 36-hour sprint.',
        category: 'Hackathon',
        organization: 'AI Club',
        venue: 'Main Auditorium, Block A',
        date: '2026-10-18',
        start_time: '09:00',
        end_time: '21:00',
        tags: ['AI', 'Machine Learning'],
        registration_link: 'https://forms.example.com/ai-hackathon',
        eligibility: 'All UG and PG students',
        capacity: '100',
        contact_email: 'organizer@example.com',
      },
      warnings: [],
      confidence: 0.9,
      processing_time_ms: 100,
    });

    render(wrapWithProviders(<CreateEventPage />));

    const announcement = screen.getByPlaceholderText(/Paste event announcement text/i);
    fireEvent.change(announcement, { target: { value: 'Some announcement text' } });

    const extractButton = screen.getByRole('button', { name: /Extract Event Details/i });
    fireEvent.click(extractButton);

    await waitFor(() => {
      expect(screen.getByLabelText(/Event Title/i)).toHaveValue('AI Hackathon 2026');
    });

    expect(screen.getByLabelText(/Description/i)).toHaveValue('Join 500+ students in a 36-hour sprint.');
    expect(screen.getByLabelText(/Category/i)).toHaveValue('Hackathon');
    expect(screen.getByLabelText(/Venue \/ Location/i)).toHaveValue('Main Auditorium, Block A');
    expect(screen.getByLabelText(/Event Date/i)).toHaveValue('2026-10-18');
    expect(screen.getByLabelText(/Start Time/i)).toHaveValue('09:00');
    expect(screen.getByLabelText(/End Time/i)).toHaveValue('21:00');
    expect(screen.getByLabelText(/Tags/i)).toHaveValue('AI, Machine Learning');
    expect(screen.getByLabelText(/Registration Link/i)).toHaveValue('https://forms.example.com/ai-hackathon');
    expect(screen.getByLabelText(/Eligibility \/ Target Audience/i)).toHaveValue('All UG and PG students');
    expect(screen.getByLabelText(/Capacity/i)).toHaveValue(100);
    expect(screen.getByLabelText(/Contact Email/i)).toHaveValue('organizer@example.com');
  });
});
