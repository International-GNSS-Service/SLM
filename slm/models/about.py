from slm.models import SingletonModel
from ckeditor_uploader.fields import RichTextUploadingField


class About(SingletonModel):
    content = RichTextUploadingField(
        blank=True,
        null=False,
        default=''
    )
    class Meta:
        verbose_name = 'Page Content: About'
        verbose_name_plural = "Page Content: About"

    def __str__(self):
        return f'About Page'