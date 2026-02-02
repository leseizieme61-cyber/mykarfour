from django import forms
from cours.models import EmploiDuTemps
from .models import SoumissionCours

JOURS_SEMAINE = [
    ('lundi', 'Lundi'),
    ('mardi', 'Mardi'),
    ('mercredi', 'Mercredi'),
    ('jeudi', 'Jeudi'),
    ('vendredi', 'Vendredi'),
    ('samedi', 'Samedi'),
    ('dimanche', 'Dimanche'),
]

class EmploiDuTempsForm(forms.ModelForm):
    jour_semaine = forms.ChoiceField(
        choices=JOURS_SEMAINE, 
        label="Jour de la semaine",
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'placeholder': 'Choisissez un jour'
        })
    )

    heure_debut = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'placeholder': 'HH:MM'
        }), 
        label="Heure de début"
    )

    heure_fin = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'placeholder': 'HH:MM'
        }), 
        label="Heure de fin"
    )

    matiere = forms.CharField(
        max_length=200, 
        label="Matière", 
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'placeholder': 'Ex: Mathématiques, Français...'
        })
    )

    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200 resize-vertical',
            'placeholder': 'Description optionnelle du cours...'
        }), 
        required=False, 
        label="Description"
    )

    document = forms.FileField(
        required=False,
        label="Document associé",
        widget=forms.ClearableFileInput(attrs={
            'class': 'block w-full text-sm text-gray-700 border border-gray-300 rounded-md cursor-pointer bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-100 file:text-blue-700 hover:file:bg-blue-200 transition duration-200'
        })
    )

    actif = forms.BooleanField(
        required=False, 
        initial=True, 
        label="Créneau actif",
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2'
        })
    )

    class Meta:
        model = EmploiDuTemps
        fields = [
            'jour_semaine', 'heure_debut', 'heure_fin',
            'matiere', 'description', 'document', 'actif'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Appliquer les classes Tailwind si manquantes
        for field_name, field in self.fields.items():
            if hasattr(field, 'widget') and hasattr(field.widget, 'attrs'):
                base_input_classes = 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200'
                if isinstance(field, forms.BooleanField):
                    if 'class' not in field.widget.attrs:
                        field.widget.attrs['class'] = 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2'
                elif isinstance(field, forms.ChoiceField):
                    if 'class' not in field.widget.attrs:
                        field.widget.attrs['class'] = base_input_classes
                elif isinstance(field, forms.FileField):
                    # Le style est déjà défini plus haut
                    continue
                else:
                    if 'class' not in field.widget.attrs:
                        field.widget.attrs['class'] = base_input_classes
        
    def clean(self):
        cleaned_data = super().clean()
        heure_debut = cleaned_data.get('heure_debut')
        heure_fin = cleaned_data.get('heure_fin')
        
        if heure_debut and heure_fin:
            if heure_debut >= heure_fin:
                self.add_error('heure_fin', "L'heure de fin doit être postérieure à l'heure de début.")
            
            # Validation durée
            debut_minutes = heure_debut.hour * 60 + heure_debut.minute
            fin_minutes = heure_fin.hour * 60 + heure_fin.minute
            
            if fin_minutes - debut_minutes <= 0:
                self.add_error('heure_fin', "La durée du cours doit être positive.")
            
            if fin_minutes - debut_minutes > 6 * 60:  # max 6h
                self.add_error('heure_fin', "La durée du cours ne peut pas dépasser 6 heures.")
        
        return cleaned_data

    def clean_matiere(self):
        matiere = self.cleaned_data.get('matiere')
        if matiere:
            # Capitaliser chaque mot
            matiere = ' '.join(word.capitalize() for word in matiere.split())
            # Validation des caractères autorisés
            if not all(c.isalpha() or c.isspace() or c in "-'()" for c in matiere):
                raise forms.ValidationError("Le nom de la matière contient des caractères non autorisés.")
            if len(matiere) < 2:
                raise forms.ValidationError("Le nom de la matière doit contenir au moins 2 caractères.")
        return matiere

class SoumissionCoursForm(forms.ModelForm):
    TYPE_SOUMISSION_CHOICES = [
        ('texte', 'Texte écrit'),
        ('fichier', 'Fichier (PDF, Word, Image)'),
    ]
    
    type_soumission = forms.ChoiceField(
        choices=TYPE_SOUMISSION_CHOICES,
        label="Type de soumission",
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-[#0EA7A7] transition duration-200',
            'id': 'id_type_soumission'
        })
    )
    
    matiere = forms.CharField(
        max_length=100,
        required=True,
        label="Matière",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-[#0EA7A7] transition duration-200',
            'placeholder': 'Ex: Mathématiques, Français, Physique...',
            'list': 'matieres_suggestions'
        })
    )
    
    contenu_texte = forms.CharField(
        required=False,
        label="Contenu du cours",
        widget=forms.Textarea(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-[#0EA7A7] transition duration-200 resize-vertical',
            'rows': 8,
            'placeholder': 'Collez votre cours ici ou décrivez ce que vous avez vu en classe...\n\nExemple :\n"Aujourd\'hui nous avons étudié le théorème de Pythagore :\n- Dans un triangle rectangle, le carré de l\'hypoténuse...\n- Formule : a² + b² = c²\n- Applications pratiques..."',
            'id': 'id_contenu_texte'
        })
    )
    
    fichier = forms.FileField(
        required=False,
        label="Fichier du cours",
        widget=forms.ClearableFileInput(attrs={
            'class': 'block w-full text-sm text-gray-700 border border-gray-300 rounded-md cursor-pointer bg-gray-50 focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-[#0EA7A7] file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-[#0EA7A7] file:text-white hover:file:bg-teal-600 transition duration-200',
            'accept': '.pdf,.doc,.docx,.txt,.jpg,.jpeg,.png',
            'id': 'id_fichier'
        })
    )

    class Meta:
        model = SoumissionCours
        fields = ['type_soumission', 'matiere', 'contenu_texte', 'fichier']
    
    def __init__(self, *args, **kwargs):
        self.session = kwargs.pop('session', None)
        super().__init__(*args, **kwargs)
        
        # Si une session est fournie, pré-remplir la matière
        if self.session and not self.instance.pk:
            self.fields['matiere'].initial = self.session.emploi_temps.matiere
        
        # Ajouter des suggestions de matières
        self.fields['matiere'].widget.attrs.update({
            'list': 'matieres_suggestions'
        })
    
    def clean(self):
        cleaned_data = super().clean()
        type_soumission = cleaned_data.get('type_soumission')
        contenu_texte = cleaned_data.get('contenu_texte')
        fichier = cleaned_data.get('fichier')
        
        # Validation selon le type de soumission
        if type_soumission == 'texte':
            if not contenu_texte or len(contenu_texte.strip()) < 10:
                self.add_error('contenu_texte', 'Veuillez saisir un contenu de cours significatif (au moins 10 caractères).')
        
        elif type_soumission == 'fichier':
            if not fichier:
                self.add_error('fichier', 'Veuillez sélectionner un fichier pour votre cours.')
            else:
                # Validation du type de fichier
                extension_valide = fichier.name.lower().endswith(('.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png'))
                if not extension_valide:
                    self.add_error('fichier', 'Type de fichier non supporté. Utilisez PDF, Word, TXT, JPG ou PNG.')
                
                # Validation de la taille (max 10MB)
                if fichier.size > 10 * 1024 * 1024:
                    self.add_error('fichier', 'Le fichier est trop volumineux (max 10MB).')
        
        return cleaned_data
    
    def clean_matiere(self):
        matiere = self.cleaned_data.get('matiere')
        if matiere:
            # Nettoyer et formater la matière
            matiere = ' '.join(word.capitalize() for word in matiere.strip().split())
            if len(matiere) < 2:
                raise forms.ValidationError("Le nom de la matière doit contenir au moins 2 caractères.")
        return matiere

class SessionRevisionForm(forms.Form):
    """Formulaire pour créer une session de révision rapide"""
    
    matiere = forms.CharField(
        max_length=100,
        required=True,
        label="Matière à réviser",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-[#0EA7A7] transition duration-200',
            'placeholder': 'Quelle matière souhaitez-vous réviser ?',
            'list': 'matieres_suggestions'
        })
    )
    
    objectifs = forms.CharField(
        required=True,
        label="Objectifs de révision",
        widget=forms.Textarea(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-[#0EA7A7] transition duration-200 resize-vertical',
            'rows': 3,
            'placeholder': 'Ex: Réviser le chapitre sur les équations, Préparer l\'interro de grammaire...'
        })
    )
    
    duree = forms.IntegerField(
        min_value=15,
        max_value=180,
        initial=45,
        label="Durée prévue (minutes)",
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-[#0EA7A7] transition duration-200',
            'min': '15',
            'max': '180',
            'step': '5'
        })
    )
    
    def clean_duree(self):
        duree = self.cleaned_data.get('duree')
        if duree and duree < 15:
            raise forms.ValidationError("La durée minimum est de 15 minutes.")
        if duree and duree > 180:
            raise forms.ValidationError("La durée maximum est de 180 minutes.")
        return duree

class ChatQuestionForm(forms.Form):
    """Formulaire pour poser une question dans le chat"""
    
    question = forms.CharField(
        required=True,
        label="",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0EA7A7] focus:border-[#0EA7A7] transition duration-200 text-sm',
            'placeholder': 'Posez votre question pédagogique ici...',
            'id': 'question'
        })
    )
    
    session_id = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    niveau = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

class UploadAudioForm(forms.Form):
    """Formulaire pour uploader un fichier audio"""
    
    audio = forms.FileField(
        required=True,
        label="Fichier audio",
        widget=forms.FileInput(attrs={
            'accept': 'audio/*',
            'class': 'hidden',
            'id': 'audioInput'
        })
    )