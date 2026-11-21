from datetime import timedelta
import os
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from .forms import AlerteForm, TAILLE_MAX_FICHIER
from .models import Alerte

User = get_user_model()


class AlerteModelTests(TestCase):
    def setUp(self):
        self.agent = User.objects.create_user(
            username='agent_test',
            password='Password123!',
            role=User.Role.AGENT,
        )

    def test_creer_alerte_modele(self):
        expiration = timezone.now() + timedelta(days=2)
        alerte = Alerte.objects.create(
            titre="Alerte Canicule",
            contenu="Consignes d'hydratation et vigilance météo pour tous les citoyens.",
            niveau_urgence=Alerte.Urgence.CRITIQUE,
            date_expiration=expiration,
            auteur=self.agent,
        )
        self.assertEqual(alerte.titre, "Alerte Canicule")
        self.assertEqual(alerte.niveau_urgence, Alerte.Urgence.CRITIQUE)
        self.assertTrue(alerte.est_active)
        self.assertFalse(alerte.est_expiree)
        self.assertEqual(alerte.badge_classe, "badge-critique")
        self.assertIn("Alerte Canicule", str(alerte))
        self.assertIn("Critique", str(alerte))

    def test_alerte_expiree(self):
        passe = timezone.now() - timedelta(days=1)
        alerte = Alerte.objects.create(
            titre="Travaux passés",
            contenu="Les travaux de voirie sont terminés.",
            niveau_urgence=Alerte.Urgence.FAIBLE,
            date_expiration=passe,
            auteur=self.agent,
        )
        self.assertFalse(alerte.est_active)
        self.assertTrue(alerte.est_expiree)
        self.assertEqual(alerte.badge_classe, "badge-faible")


class AlerteFormTests(TestCase):
    def setUp(self):
        self.agent = User.objects.create_user(
            username='agent_form',
            password='Password123!',
            role=User.Role.AGENT,
        )

    def test_formulaire_valide_sans_fichier(self):
        future_date = timezone.now() + timedelta(days=3)
        data = {
            'titre': "Coupure d'eau programmée",
            'contenu': "Une coupure d'eau aura lieu dans le secteur nord entre 14h et 18h.",
            'niveau_urgence': Alerte.Urgence.MOYENNE,
            'date_expiration': future_date.strftime('%Y-%m-%dT%H:%M'),
        }
        form = AlerteForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_date_expiration_dans_le_passe(self):
        passe = timezone.now() - timedelta(days=1)
        data = {
            'titre': "Avis météo",
            'contenu': "Consignes de sécurité suite à tempête.",
            'niveau_urgence': Alerte.Urgence.ELEVEE,
            'date_expiration': passe.strftime('%Y-%m-%dT%H:%M'),
        }
        form = AlerteForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('date_expiration', form.errors)
        self.assertIn("ultérieure", form.errors['date_expiration'][0])

    def test_titre_trop_court(self):
        future_date = timezone.now() + timedelta(days=1)
        data = {
            'titre': "Test",
            'contenu': "Consignes de sécurité détaillées pour le quartier.",
            'niveau_urgence': Alerte.Urgence.FAIBLE,
            'date_expiration': future_date.strftime('%Y-%m-%dT%H:%M'),
        }
        form = AlerteForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('titre', form.errors)

    def test_piece_jointe_valide(self):
        future_date = timezone.now() + timedelta(days=2)
        pdf_file = SimpleUploadedFile("arrete_municipal.pdf", b"%PDF-1.4 test document content", content_type="application/pdf")
        data = {
            'titre': "Arrêté de circulation",
            'contenu': "Veuillez trouver ci-joint l'arrêté municipal relatif à la circulation.",
            'niveau_urgence': Alerte.Urgence.ELEVEE,
            'date_expiration': future_date.strftime('%Y-%m-%dT%H:%M'),
        }
        file_data = {'piece_jointe': pdf_file}
        form = AlerteForm(data=data, files=file_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_piece_jointe_extension_invalide(self):
        future_date = timezone.now() + timedelta(days=2)
        script_file = SimpleUploadedFile("script_malveillant.exe", b"binarycontent", content_type="application/octet-stream")
        data = {
            'titre': "Arrêté de circulation",
            'contenu': "Veuillez trouver ci-joint l'arrêté municipal relatif aux travaux.",
            'niveau_urgence': Alerte.Urgence.MOYENNE,
            'date_expiration': future_date.strftime('%Y-%m-%dT%H:%M'),
        }
        file_data = {'piece_jointe': script_file}
        form = AlerteForm(data=data, files=file_data)
        self.assertFalse(form.is_valid())
        self.assertIn('piece_jointe', form.errors)
        self.assertIn("n'est pas autorisé", form.errors['piece_jointe'][0])

    def test_piece_jointe_taille_excessive(self):
        future_date = timezone.now() + timedelta(days=2)
        large_content = b"0" * (TAILLE_MAX_FICHIER + 1024)
        large_file = SimpleUploadedFile("gros_fichier.pdf", large_content, content_type="application/pdf")
        data = {
            'titre': "Grand plan communal",
            'contenu': "Veuillez trouver ci-joint le plan d'urbanisme grand format.",
            'niveau_urgence': Alerte.Urgence.FAIBLE,
            'date_expiration': future_date.strftime('%Y-%m-%dT%H:%M'),
        }
        file_data = {'piece_jointe': large_file}
        form = AlerteForm(data=data, files=file_data)
        self.assertFalse(form.is_valid())
        self.assertIn('piece_jointe', form.errors)
        self.assertIn("trop volumineux", form.errors['piece_jointe'][0])


class AlerteViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.citoyen = User.objects.create_user(
            username='citoyen_normal',
            password='Password123!',
            role=User.Role.CITOYEN,
        )
        self.agent = User.objects.create_user(
            username='agent_officiel',
            password='Password123!',
            role=User.Role.AGENT,
        )
        # Note: agent.save() automatically sets is_staff = True for agents

    def test_acces_anonyme_creer_alerte_redirige(self):
        url = reverse('actualites:creer_alerte')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_acces_citoyen_bloque_creer_alerte(self):
        self.client.login(username='citoyen_normal', password='Password123!')
        url = reverse('actualites:creer_alerte')
        response = self.client.get(url)
        # Non-staff user redirected by @staff_member_required
        self.assertEqual(response.status_code, 302)

    def test_staff_non_agent_bloque_creer_alerte(self):
        user_staff = User.objects.create_user(
            username='staff_non_agent',
            password='Password123!',
            role=User.Role.CITOYEN,
            is_staff=True,
        )
        self.client.login(username='staff_non_agent', password='Password123!')
        url = reverse('actualites:creer_alerte')
        response = self.client.get(url, follow=True)
        self.assertTemplateUsed(response, 'actualities/liste_alertes.html')
        self.assertContains(response, "Accès refusé")

    def test_acces_agent_autorise_creer_alerte_get(self):
        self.client.login(username='agent_officiel', password='Password123!')
        url = reverse('actualites:creer_alerte')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'actualities/creer_alerte.html')
        self.assertContains(response, "Publier une alerte")
        self.assertContains(response, 'enctype="multipart/form-data"')

    def test_publication_alerte_agent_post(self):
        self.client.login(username='agent_officiel', password='Password123!')
        url = reverse('actualites:creer_alerte')
        future_date = timezone.now() + timedelta(days=5)
        pdf = SimpleUploadedFile("avis_alerte.pdf", b"%PDF-1.4 test document content", content_type="application/pdf")

        data = {
            'titre': "Avis de tempête et vents violents",
            'contenu': "Des rafales de vent dépassant les 90 km/h sont prévues dans la commune.",
            'niveau_urgence': Alerte.Urgence.CRITIQUE,
            'date_expiration': future_date.strftime('%Y-%m-%dT%H:%M'),
            'piece_jointe': pdf,
        }
        response = self.client.post(url, data=data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'actualities/detail_alerte.html')
        self.assertContains(response, "Avis de tempête et vents violents")
        self.assertContains(response, "Critique")

        alerte = Alerte.objects.get(titre="Avis de tempête et vents violents")
        self.assertEqual(alerte.auteur, self.agent)
        self.assertEqual(alerte.niveau_urgence, Alerte.Urgence.CRITIQUE)
        self.assertTrue(alerte.piece_jointe)

    def test_liste_alertes_publique(self):
        expiration = timezone.now() + timedelta(days=2)
        Alerte.objects.create(
            titre="Alerte pollution",
            contenu="Pic d'ozone enregistré, merci de réduire la vitesse.",
            niveau_urgence=Alerte.Urgence.MOYENNE,
            date_expiration=expiration,
            auteur=self.agent,
        )
        url = reverse('actualites:list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alerte pollution")

    def test_liste_alertes_filtre_actives_uniquement(self):
        # Alerte active
        Alerte.objects.create(
            titre="Travaux avenue Habib Bourguiba",
            contenu="Circulation ralentie en centre-ville.",
            niveau_urgence=Alerte.Urgence.MOYENNE,
            date_expiration=timezone.now() + timedelta(days=2),
            auteur=self.agent,
            est_active=True,
        )
        # Alerte expirée
        Alerte.objects.create(
            titre="Alerte ancienne terminée",
            contenu="Cet avis n'est plus valable.",
            niveau_urgence=Alerte.Urgence.FAIBLE,
            date_expiration=timezone.now() - timedelta(days=3),
            auteur=self.agent,
            est_active=False,
        )
        url = reverse('actualites:list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Travaux avenue Habib Bourguiba")
        self.assertNotContains(response, "Alerte ancienne terminée")

    def test_liste_alertes_recherche_et_urgence(self):
        alerte_coupure = Alerte.objects.create(
            titre="Coupure eau quartier Sud",
            contenu="Travaux sur le réseau principal de distribution.",
            niveau_urgence=Alerte.Urgence.ELEVEE,
            date_expiration=timezone.now() + timedelta(days=2),
            auteur=self.agent,
            est_active=True,
        )
        alerte_collecte = Alerte.objects.create(
            titre="Collecte encombrants",
            contenu="Ramassage exceptionnel ce samedi.",
            niveau_urgence=Alerte.Urgence.FAIBLE,
            date_expiration=timezone.now() + timedelta(days=2),
            auteur=self.agent,
            est_active=True,
        )
        # Recherche par mot-clé
        response = self.client.get(reverse('actualites:list') + '?q=Coupure')
        self.assertIn(alerte_coupure, response.context['alertes'])
        self.assertNotIn(alerte_collecte, response.context['alertes'])

        # Filtre par niveau d'urgence
        response = self.client.get(reverse('actualites:list') + '?urgence=elevee')
        self.assertIn(alerte_coupure, response.context['alertes'])
        self.assertNotIn(alerte_collecte, response.context['alertes'])

    def test_bandeau_alerte_urgente_dans_base_html(self):
        # Création d'une alerte critique
        Alerte.objects.create(
            titre="Inondations - Restez chez vous",
            contenu="Vigilance rouge crue subite dans la région.",
            niveau_urgence=Alerte.Urgence.CRITIQUE,
            date_expiration=timezone.now() + timedelta(days=1),
            auteur=self.agent,
            est_active=True,
        )
        # Vérification que le bandeau apparaît même sur la page d'accueil (base.html)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ALERTE URGENTE")
        self.assertContains(response, "Inondations - Restez chez vous")

    def test_detail_alerte_avec_telechargement_piece_jointe(self):
        pdf = SimpleUploadedFile("arrete_securite.pdf", b"%PDF-1.4 contenu officiel", content_type="application/pdf")
        alerte = Alerte.objects.create(
            titre="Arrêté de périmètre de sécurité",
            contenu="Détails complets des mesures de sécurité prises par la mairie.",
            niveau_urgence=Alerte.Urgence.ELEVEE,
            date_expiration=timezone.now() + timedelta(days=4),
            piece_jointe=pdf,
            auteur=self.agent,
            est_active=True,
        )
        url = reverse('actualites:detail_alerte', kwargs={'pk': alerte.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'actualities/detail_alerte.html')
        self.assertContains(response, "Arrêté de périmètre de sécurité")
        self.assertContains(response, "Télécharger le document joint")
        self.assertContains(response, alerte.piece_jointe.url)

    def test_modifier_alerte_acces_anonyme_redirige(self):
        alerte = Alerte.objects.create(
            titre="Avis initial",
            contenu="Contenu initial à modifier plus tard.",
            niveau_urgence=Alerte.Urgence.MOYENNE,
            date_expiration=timezone.now() + timedelta(days=3),
            auteur=self.agent,
            est_active=True,
        )
        url = reverse('actualites:modifier_alerte', kwargs={'pk': alerte.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_modifier_alerte_citoyen_bloque(self):
        self.client.login(username='citoyen_normal', password='Password123!')
        alerte = Alerte.objects.create(
            titre="Avis initial",
            contenu="Contenu initial à modifier plus tard.",
            niveau_urgence=Alerte.Urgence.MOYENNE,
            date_expiration=timezone.now() + timedelta(days=3),
            auteur=self.agent,
            est_active=True,
        )
        url = reverse('actualites:modifier_alerte', kwargs={'pk': alerte.pk})
        response = self.client.get(url, follow=True)
        self.assertTemplateUsed(response, 'actualities/liste_alertes.html')
        self.assertContains(response, "Accès refusé")

    def test_modifier_alerte_agent_get_formulaire_pre_rempli(self):
        self.client.login(username='agent_officiel', password='Password123!')
        alerte = Alerte.objects.create(
            titre="Titre original à corriger",
            contenu="Description détaillée initiale des travaux sur le pont.",
            niveau_urgence=Alerte.Urgence.MOYENNE,
            date_expiration=timezone.now() + timedelta(days=4),
            auteur=self.agent,
            est_active=True,
        )
        url = reverse('actualites:modifier_alerte', kwargs={'pk': alerte.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'actualities/modifier_alerte.html')
        self.assertContains(response, "Titre original à corriger")
        self.assertContains(response, "Description détaillée initiale des travaux")

    def test_modifier_alerte_agent_post_mise_a_jour_et_horodatage(self):
        self.client.login(username='agent_officiel', password='Password123!')
        future_date = timezone.now() + timedelta(days=5)
        alerte = Alerte.objects.create(
            titre="Titre initial",
            contenu="Contenu avant correction par l'agent municipal.",
            niveau_urgence=Alerte.Urgence.FAIBLE,
            date_expiration=future_date,
            auteur=self.agent,
            est_active=True,
        )
        date_initiale_maj = alerte.date_mise_a_jour

        # Modification POST
        url = reverse('actualites:modifier_alerte', kwargs={'pk': alerte.pk})
        nouvelle_date_exp = timezone.now() + timedelta(days=7)
        data = {
            'titre': "Titre corrigé et mis à jour",
            'contenu': "Nouveau contenu révisé avec consignes complémentaires.",
            'niveau_urgence': Alerte.Urgence.ELEVEE,
            'date_expiration': nouvelle_date_exp.strftime('%Y-%m-%dT%H:%M'),
        }
        response = self.client.post(url, data=data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'actualities/detail_alerte.html')
        self.assertContains(response, "Titre corrigé et mis à jour")
        self.assertContains(response, "Mis à jour le")

        alerte.refresh_from_db()
        self.assertEqual(alerte.titre, "Titre corrigé et mis à jour")
        self.assertEqual(alerte.niveau_urgence, Alerte.Urgence.ELEVEE)
        self.assertGreaterEqual(alerte.date_mise_a_jour, date_initiale_maj)
