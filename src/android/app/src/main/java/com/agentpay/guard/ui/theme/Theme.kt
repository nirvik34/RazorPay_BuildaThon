package com.agentpay.guard.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

object GuardColors {
    val Background = Color(0xFFF7F9FC)
    val Foreground = Color(0xFF101828)
    val Brand = Color(0xFF2563EB)
    val BrandDark = Color(0xFF1D4ED8)
    val Muted = Color(0xFF667085)
    val Border = Color(0xFFE4E7EC)
    val Card = Color(0xFFFFFFFF)
    val Navy = Color(0xFF0B1220)

    val Success = Color(0xFF12B76A)
    val SuccessBg = Color(0xFFECFDF3)
    val SuccessBorder = Color(0xFFA6F4C5)
    val SuccessText = Color(0xFF067647)

    val Danger = Color(0xFFF04438)
    val DangerBg = Color(0xFFFEF3F2)
    val DangerBorder = Color(0xFFFECDCA)
    val DangerText = Color(0xFFB42318)

    val Warning = Color(0xFFF79009)
    val WarningBg = Color(0xFFFFFAEB)
    val WarningBorder = Color(0xFFFEDF89)
    val WarningText = Color(0xFFB54708)

    val Info = Color(0xFF2E90FA)
    val InfoBg = Color(0xFFEFF8FF)

    val Purple = Color(0xFF7F56D9)
    val PurpleBg = Color(0xFFF4F3FF)
}

private val LightColors = lightColorScheme(
    primary = GuardColors.Brand,
    onPrimary = Color.White,
    secondary = GuardColors.Navy,
    background = GuardColors.Background,
    onBackground = GuardColors.Foreground,
    surface = GuardColors.Card,
    onSurface = GuardColors.Foreground,
    surfaceVariant = GuardColors.Background,
    onSurfaceVariant = GuardColors.Muted,
    error = GuardColors.Danger,
    outline = GuardColors.Border
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF3B82F6),
    background = Color(0xFF080C14),
    onBackground = Color(0xFFF2F4F7),
    surface = Color(0xFF101828),
    onSurface = Color(0xFFF2F4F7),
    error = Color(0xFFF97066),
    outline = Color(0xFF1D2939)
)

val GuardTypography = Typography(
    headlineSmall = TextStyle(
        fontWeight = FontWeight.Bold,
        fontSize = 24.sp,
        letterSpacing = (-0.02).sp
    ),
    titleMedium = TextStyle(
        fontWeight = FontWeight.SemiBold,
        fontSize = 16.sp,
        letterSpacing = (-0.01).sp
    ),
    bodyMedium = TextStyle(fontSize = 14.sp, lineHeight = 21.sp),
    bodySmall = TextStyle(fontSize = 12.sp, lineHeight = 18.sp),
    labelSmall = TextStyle(
        fontFamily = FontFamily.Monospace,
        fontSize = 11.sp
    )
)

@Composable
fun AgentPayTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (isSystemInDarkTheme()) DarkColors else LightColors,
        typography = GuardTypography,
        content = content
    )
}
