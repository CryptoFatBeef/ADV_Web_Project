from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class ChatbotView(LoginRequiredMixin, TemplateView):
    template_name = 'partials/coming_soon.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Chatbot'
        return context
