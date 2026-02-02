from django import forms
from .models import Cours, Quiz, Question, Choice


class CoursForm(forms.ModelForm):
    class Meta:
        model = Cours
        fields = ['titre', 'matiere', 'niveau', 'contenu', 'fichier', 'objectifs', 'duree_estimee', 'est_public', 'tags']
        
        widgets = {
            'titre': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-transparent text-black',
                'placeholder': 'Ex: Introduction aux mathématiques'
            }),
            'matiere': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-transparent text-black'
            }),
            'niveau': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-transparent text-black'
            }),
            'contenu': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-transparent text-black',
                'placeholder': 'Décrivez le contenu du cours...',
                'rows': 8
            }),
            'fichier': forms.FileInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-transparent text-black file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-[#0EA7A7] file:text-white hover:file:bg-teal-600'
            }),
            'objectifs': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-transparent text-black',
                'placeholder': 'Objectifs pédagogiques...',
                'rows': 4
            }),
            'duree_estimee': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-transparent text-black',
                'placeholder': 'Durée en minutes'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-transparent text-black',
                'placeholder': 'Ex: algèbre, géométrie, équations'
            }),
        }
        labels = {
            'titre': 'Titre du cours',
            'matiere': 'Matière',
            'niveau': 'Niveau scolaire',
            'contenu': 'Contenu détaillé',
            'fichier': 'Document du cours',
            'objectifs': 'Objectifs pédagogiques',
            'duree_estimee': 'Durée estimée (minutes)',
            'est_public': 'Cours public',
            'tags': 'Mots-clés',
        }
        help_texts = {
            'fichier': 'Formats acceptés: PDF, Word, images (max 10MB)',
            'tags': 'Séparez les mots-clés par des virgules',
            'est_public': 'Si cochée, le cours est visible par tous les élèves du niveau',
        }



class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['titre', 'description', 'cours', 'duree', 'points_max']
        widgets = {
            'titre': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-transparent text-black',
                'placeholder': 'Titre du quiz'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-transparent text-black',
                'rows': 3,
                'placeholder': 'Description du quiz...'
            }),
            'cours': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-transparent text-black'
            }),
            'duree': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-transparent text-black',
                'placeholder': 'Durée en minutes'
            }),
            'points_max': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-transparent text-black',
                'placeholder': 'Points maximum'
            }),
        }

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['texte', 'ordre', 'points', 'explication']
        widgets = {
            'texte': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-transparent text-black',
                'rows': 3,
                'placeholder': 'Entrez la question...'
            }),
            'ordre': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-transparent text-black',
                'min': 1
            }),
            'points': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-transparent text-black',
                'min': 1,
                'max': 10
            }),
            'explication': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-transparent text-black',
                'rows': 2,
                'placeholder': 'Explication qui sera montrée après la réponse...'
            }),
        }
        labels = {
            'texte': 'Question',
            'ordre': 'Ordre dans le quiz',
            'points': 'Points attribués',
            'explication': 'Explication de la réponse',
        }
        help_texts = {
            'points': 'Nombre de points pour une réponse correcte',
            'explication': 'Optionnel - Sera affiché après que l\'élève ait répondu',
        }

        
class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['texte', 'est_correcte', 'ordre']
        widgets = {
            'texte': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-transparent text-black',
                'placeholder': 'Texte du choix...'
            }),
            'ordre': forms.NumberInput(attrs={
                'class': 'w-16 px-2 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-transparent text-black'
            }),
        }