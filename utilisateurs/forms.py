from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import authenticate
from .models import Utilisateur, Eleve, Parent, Professeur
from django.core.exceptions import ValidationError

# ========================
# Formulaire Inscription
# ========================
class InscriptionForm(UserCreationForm):
    TYPE_UTILISATEUR_CHOICES = [
        ('élève', 'Élève'),
        ('parent', 'Parent'),
        ('professeur', 'Professeur'),
    ]

    type_utilisateur = forms.ChoiceField(
        choices=TYPE_UTILISATEUR_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'inline-block'}),
        label=""
    )

    class Meta:
        model = Utilisateur
        fields = ('username','last_name','first_name','email','telephone','type_utilisateur','password1','password2')

    # Champs stylés Tailwind
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-md text-black', 'placeholder': 'Nom d\'identifiant'}), label="")
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-md text-black', 'placeholder': 'Nom de famille'}), label="")
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-md text-black', 'placeholder': 'Prénom'}), label="")
    email = forms.EmailField(widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-md text-black', 'placeholder': 'Email'}), label="")
    telephone = forms.CharField(widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-md text-black', 'placeholder': 'Numéro de téléphone'}), label="")
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'w-full px-4 py-2 border rounded-md text-black', 'placeholder': 'Mot de passe'}), label="")
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'w-full px-4 py-2 border rounded-md text-black', 'placeholder': 'Confirmer mot de passe'}), label="")

    def clean_email(self):
        email = self.cleaned_data.get("email")
        # Vérifie unicité
        if Utilisateur.objects.filter(email=email).exists():
            raise ValidationError("Un compte avec cet email existe déjà.")

        # Vérification basique du format d'email (sans DNS)
        if '@' not in email or '.' not in email.split('@')[-1]:
            raise ValidationError("Veuillez entrer une adresse email valide.")
        
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error('password2', "Les mots de passe ne correspondent pas.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.type_utilisateur = self.cleaned_data['type_utilisateur']

        if commit:
            user.save()
        return user
    
# ========================
# Formulaire Connexion
# ========================
class ConnexionForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-md text-black', 'placeholder': 'Nom d\'identifiant'}), label="")
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'w-full px-4 py-2 border rounded-md text-black', 'placeholder': 'Mot de passe'}), label="")

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        if username and password:
            user = authenticate(username=username, password=password)
            if user is None:
                raise forms.ValidationError("Nom d'utilisateur ou mot de passe incorrect.")
            elif not user.is_active:
                raise forms.ValidationError("Ce compte est désactivé.")
        return cleaned_data

# ========================
# Formulaire Profil Élève (Collège et Lycée uniquement)
# ========================
TAILWIND_INPUT_CLASS = "block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:ring focus:ring-primary/30 focus:outline-none transition text-black"
TAILWIND_SELECT_CLASS = "block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:ring focus:ring-primary/30 focus:outline-none transition text-black"

class EleveProfilForm(forms.ModelForm):
    etablissement = forms.CharField(
        required=False,
        label="Établissement",
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': "Nom de l'établissement", 'id': 'id_etablissement'})
    )
    # utiliser directement les constantes du modèle
    niveau = forms.ChoiceField(
        choices=[('', '---------')] + Eleve.NIVEAUX,
        required=False,
        label="Niveau scolaire",
        widget=forms.Select(attrs={'class': TAILWIND_SELECT_CLASS, 'id': 'id_niveau'})
    )
    classe = forms.ChoiceField(
        choices=[('', '---------')],
        required=False,
        label="Classe",
        widget=forms.Select(attrs={'class': TAILWIND_SELECT_CLASS, 'id': 'id_classe'})
    )

    class Meta:
        model = Eleve
        fields = ['etablissement', 'niveau', 'classe']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # initialisation existante
        if self.instance and self.instance.pk:
            self.fields['etablissement'].initial = self.instance.etablissement
            self.fields['niveau'].initial = self.instance.niveau
            self.fields['classe'].initial = self.instance.classe

        # déterminer niveau (POST > initial > instance)
        niveau = None
        if self.data and self.data.get('niveau'):
            niveau = self.data.get('niveau')
        elif self.initial.get('niveau'):
            niveau = self.initial.get('niveau')
        elif self.instance and getattr(self.instance, 'niveau', None):
            niveau = self.instance.niveau

        # normaliser valeur
        nk = (str(niveau).lower() if niveau else '')
        nk = nk.replace('é', 'e').replace('è', 'e').replace('ê', 'e')

        # mettre à jour les choix selon les constantes du modèle
        if nk == Eleve.NIVEAU_COLLEGE or nk == 'college' :
            self.fields['classe'].choices = [('', '---------')] + Eleve.CLASSES_COLLEGE
        elif nk == Eleve.NIVEAU_LYCEE or nk == 'lycee':
            self.fields['classe'].choices = [('', '---------')] + Eleve.CLASSES_LYCEE
        else:
            self.fields['classe'].choices = [('', '---------')]

# ========================
# Formulaire Profil Parent
# ========================
class ParentProfilForm(forms.ModelForm):
    class Meta:
        model = Parent
        fields = []

# ========================
# Formulaire Lien Parent/Élève
# ========================
class LienParentEleveForm(forms.Form):
    code_eleve = forms.CharField(
        max_length=20, 
        label="Code de l'élève", 
        help_text="Demandez le code à votre enfant pour le lier à votre compte.",
        widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-md text-black'})
    )

    def __init__(self, *args, **kwargs):
        self.parent = kwargs.pop('parent', None)
        super().__init__(*args, **kwargs)

    def clean_code_eleve(self):
        code_eleve = self.cleaned_data['code_eleve']
        try:
            eleve = Eleve.objects.get(code_parrainage=code_eleve)
        except Eleve.DoesNotExist:
            raise forms.ValidationError("Code invalide. Aucun élève trouvé avec ce code.")
        
        if self.parent and eleve in self.parent.eleves.all():
            raise forms.ValidationError("Cet élève est déjà lié à votre compte.")
        
        return code_eleve

    def save(self, parent):
        code_eleve = self.cleaned_data['code_eleve']
        eleve = Eleve.objects.get(code_parrainage=code_eleve)
        parent.eleves.add(eleve)
        return eleve


# ========================
# Formulaire Professeur
# ========================

class ProfesseurProfilForm(forms.ModelForm):
    class Meta:
        model = Professeur
        fields = ['matiere_principale', 'niveau_enseigne', 'biographie', 'experience', 'cv']
        widgets = {
            'matiere_principale': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-black'
            }),
            'niveau_enseigne': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-black'
            }),
            'biographie': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-black',
                'rows': 4,
                'placeholder': 'Décrivez votre parcours, votre méthode d\'enseignement...'
            }),
            'experience': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-black',
                'min': 0,
                'max': 50
            }),
            'cv': forms.FileInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'accept': '.pdf,.doc,.docx'
            }),
        }
        labels = {
            'matiere_principale': 'Matière principale enseignée',
            'niveau_enseigne': 'Niveau enseigné',
            'biographie': 'Présentation et biographie',
            'experience': "Années d'expérience",
            'cv': 'CV (PDF, DOC)',
        }


class ParentNotificationsForm(forms.ModelForm):
    """Formulaire pour les préférences de notifications des parents"""
    class Meta:
        model = Parent
        fields = [
            'notifications_quotidiennes',
            'notifications_hebdomadaires', 
            'notifications_evaluations',
            'notifications_quiz',
        ]
        widgets = {
            'notifications_quotidiennes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notifications_hebdomadaires': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notifications_evaluations': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notifications_quiz': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'notifications_quotidiennes': 'Résumé quotidien des activités',
            'notifications_hebdomadaires': 'Rapport hebdomadaire détaillé',
            'notifications_evaluations': 'Alertes nouvelles évaluations',
            'notifications_quiz': 'Alertes nouveaux quiz réalisés',
        }