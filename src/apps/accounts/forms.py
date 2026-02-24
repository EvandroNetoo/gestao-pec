from django import forms
from django.contrib.auth.forms import AuthenticationForm, BaseUserCreationForm

from accounts.models import User


class SignupForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = [
            'email',
        ]

    def clean_email(self):
        email = self.cleaned_data.get('email', '')
        return email.lower()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs['autofocus'] = True

        placeholders = {
            'email': 'Digite seu email',
            'password1': 'Digite sua senha',
            'password2': 'Confirme sua senha',
        }
        for field_name, field in self.fields.items():
            field.widget.attrs['placeholder'] = placeholders[field_name]
            field.required = True


class SigninForm(AuthenticationForm):
    def get_invalid_login_error(self):
        return forms.ValidationError(
            'Credenciais inválidas.',
        )

    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        return username.lower()

    def __init__(self, *args, **kwargs):
        kwargs['use_required_attribute'] = False
        super().__init__(*args, **kwargs)

        self.fields['username'].widget.attrs['autofocus'] = False

        placeholders = {
            'username': 'Digite seu email',
            'password': 'Digite sua senha',
        }
        for field_name, field in self.fields.items():
            field.widget.attrs['placeholder'] = placeholders[field_name]


class WidgetsShowcaseForm(forms.Form):
    text = forms.CharField(
        label='Texto',
        help_text='Digite de 3 a 40 caracteres.',
        min_length=3,
        max_length=40,
    )
    email = forms.EmailField(
        label='Email',
        help_text='Use um email valido (ex: nome@ifes.edu.br).',
    )
    url = forms.URLField(
        label='URL',
        required=False,
        help_text='Opcional. Ex: https://www.ifes.edu.br',
    )
    number = forms.IntegerField(
        label='Numero',
        help_text='Apenas numeros inteiros entre 1 e 10.',
        min_value=1,
        max_value=10,
    )
    decimal = forms.DecimalField(
        label='Decimal',
        help_text='Exemplo: 12.50 (ate 2 casas).',
        max_digits=6,
        decimal_places=2,
    )
    password = forms.CharField(
        label='Senha',
        help_text='Minimo de 6 caracteres.',
        min_length=6,
        widget=forms.PasswordInput,
    )
    textarea = forms.CharField(
        label='Mensagem',
        help_text='Escreva uma mensagem curta.',
        widget=forms.Textarea,
    )

    date = forms.DateField(
        label='Data',
        help_text='Escolha uma data.',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    datetime = forms.DateTimeField(
        label='Data e hora',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        help_text='Escolha data e hora.',
    )
    time = forms.TimeField(
        label='Hora',
        help_text='Escolha um horario.',
        widget=forms.TimeInput(attrs={'type': 'time'}),
    )

    checkbox = forms.BooleanField(
        label='Aceito os termos',
        help_text='Obrigatorio para continuar.',
    )
    radio = forms.ChoiceField(
        label='Opcao (radio)',
        help_text='Selecione uma opcao.',
        widget=forms.RadioSelect,
        choices=[('a', 'Opcao A'), ('b', 'Opcao B')],
    )
    select = forms.ChoiceField(
        label='Selecao',
        help_text='Escolha uma opcao da lista.',
        choices=[('1', 'Um'), ('2', 'Dois'), ('3', 'Tres')],
    )
    select_multiple = forms.MultipleChoiceField(
        label='Selecao multipla',
        widget=forms.SelectMultiple,
        choices=[('1', 'Um'), ('2', 'Dois'), ('3', 'Tres')],
        help_text='Selecione uma ou mais opcoes.',
    )

    file = forms.FileField(
        label='Arquivo',
        required=False,
        help_text='Envie qualquer arquivo (opcional).',
    )
    image = forms.ImageField(
        label='Imagem',
        required=False,
        help_text='Envie uma imagem (opcional).',
    )

    hidden = forms.CharField(
        label='Oculto',
        widget=forms.HiddenInput,
        required=False,
        initial='valor-oculto',
    )



    def __init__(self, *args, **kwargs):
        kwargs['use_required_attribute'] = False
        super().__init__(*args, **kwargs)

        self.fields['text'].error_messages.update(
            {
                'required': 'Texto e obrigatorio.',
                'min_length': 'Texto muito curto.',
                'max_length': 'Texto muito longo.',
            },
        )
        self.fields['email'].error_messages.update(
            {
                'required': 'Email e obrigatorio.',
                'invalid': 'Email invalido.',
            },
        )
        self.fields['url'].error_messages.update({'invalid': 'URL invalida.'})
        self.fields['number'].error_messages.update(
            {
                'required': 'Numero e obrigatorio.',
                'min_value': 'O numero deve ser maior ou igual a 1.',
                'max_value': 'O numero deve ser menor ou igual a 10.',
                'invalid': 'Digite um numero inteiro valido.',
            },
        )
        self.fields['decimal'].error_messages.update(
            {
                'required': 'Decimal e obrigatorio.',
                'invalid': 'Decimal invalido.',
                'max_digits': 'Numero com muitos digitos.',
                'max_decimal_places': 'Use no maximo 2 casas decimais.',
                'max_whole_digits': 'Use no maximo 4 digitos inteiros.',
            },
        )
        self.fields['password'].error_messages.update(
            {
                'required': 'Senha e obrigatoria.',
                'min_length': 'Senha muito curta.',
            },
        )
        self.fields['textarea'].error_messages.update(
            {'required': 'Mensagem e obrigatoria.'},
        )
        self.fields['date'].error_messages.update(
            {'required': 'Data e obrigatoria.', 'invalid': 'Data invalida.'},
        )
        self.fields['datetime'].error_messages.update(
            {
                'required': 'Data e hora e obrigatoria.',
                'invalid': 'Data e hora invalida.',
            },
        )
        self.fields['time'].error_messages.update(
            {'required': 'Hora e obrigatoria.', 'invalid': 'Hora invalida.'},
        )
        self.fields['checkbox'].error_messages.update(
            {'required': 'Voce precisa aceitar os termos.'},
        )
        self.fields['radio'].error_messages.update(
            {'required': 'Selecione uma opcao.'},
        )
        self.fields['select'].error_messages.update(
            {'required': 'Selecao obrigatoria.'},
        )
        self.fields['select_multiple'].error_messages.update(
            {'required': 'Selecione ao menos uma opcao.'},
        )
        self.fields['file'].error_messages.update(
            {'invalid': 'Arquivo invalido.'},
        )
        self.fields['image'].error_messages.update(
            {'invalid_image': 'Imagem invalida.'},
        )

        self.add_error(
            None,
            'Erro de formulario: numero 7 nao e permitido com este texto.',
        )